import asyncio
from typing import Dict

import torch
import torch.nn.functional as F
from pathlib import Path
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from model.utils.JsonExtractor import JsonExtractor
from model.utils.OpenRouter import OpenRouter
from model.transformer import TransformerClassifier, tokenizer, MAX_LENGTH
from model.utils.Tokenizer import analyze_text_with_gradcam

load_dotenv()


class EvaluatorSchema(BaseModel):
    score: int = Field(description='Given the text, return score from 0 to 100 indicating how human-like the text is')


class ExplanationSchema(BaseModel):
    explanation: str = Field(..., description='Detailed analysis of why the detector scored this way')


class SuggestionsSchema(BaseModel):
    examples: str = Field(
        ...,
        description='Recommendations in Russian with examples'
                    ' of token fixes and suggestions to enhance humanity'
    )


evaluator_template = """
Analyze the provided text and return a score from 0 to 100, where:
0 = Definitely AI-written,
100 = Definitely human-written.

{format_instructions}

Text to Analyze:
{text}
"""
evaluator_parser = PydanticOutputParser(pydantic_object=EvaluatorSchema)
evaluator_prompt = PromptTemplate(
    template=evaluator_template,
    input_variables=['text'],
    partial_variables={'format_instructions': evaluator_parser.get_format_instructions()},
)

explanation_template = """
You are an expert interpreter of AI Text Detector outputs.
The detector has assigned the following input text a human-likeness score of {score}%:

=== Begin Input Text ===
{text}
=== End Input Text ===

Please provide a single, comprehensive explanation—of at least 150 words—describing exactly why the model evaluated
this text this way.
Focus on the internal criteria of the neural detector, such as:
- Vocabulary richness (diversity of words, rare/idiomatic expressions)
- Syntactic complexity (sentence length variation, clauses, punctuation)
- Semantic coherence (logical flow, thematic consistency)
- Stylistic markers (tone, personalization, emotional nuance)
- Repetitive or templated phrasing indicative of AI output

**Answer in Russian.**
**Format the explanation into clear paragraphs**, using an empty line to separate each paragraph.

Return strictly a JSON object in this exact format:
{{
  "explanation": "<your detailed analysis in Russian, nicely broken into paragraphs>"
}}
Do not include any additional keys, comments or free-form text outside of this JSON.
"""
explanation_parser = PydanticOutputParser(pydantic_object=ExplanationSchema)
explanation_prompt = PromptTemplate(
    template=explanation_template,
    input_variables=['text', 'score'],
)


suggestions_template = """
You are a text refinement assistant specialized in improving the human-likeness of AI-detected text.
Input:
- A human-likeness score: {score}%
- A detailed explanation in Russian: {explanation}
- A JSON list of tokens with their influence scores: {tokens}

Footnote: before each token name itself, write the word “Token” in Russian.

Your task is to provide recommendations in Russian, logically separated into paragraphs. For each of the top tokens that most negatively impact human-likeness, give:
- The token itself (prefixed with “Token” in Russian)
- A brief explanation of why it lowers human-likeness
- An example of correction at the token level
- An example of a corrected sentence incorporating the improved token usage

Also, include general suggestions on how to adjust style, vocabulary, and structure to increase human-likeness.

Ensure that all corrections and examples are provided in the same language as the original text.

Return strictly a JSON object:
{{  
  "examples": "<your recommendations in Russian, paragraphs with examples>"  
}}
Do not include any other keys or extra text.
"""


suggestions_parser = PydanticOutputParser(pydantic_object=SuggestionsSchema)
suggestions_prompt = PromptTemplate(
    template=suggestions_template,
    input_variables=['score', 'explanation', 'tokens']
)


class State(TypedDict):
    text: str
    intermediate_scores: list[float]
    score: float
    explanation: str
    tokens: list[dict[str, float]]
    examples: str


EVALUATOR_WEIGHTS = {'openai/o4-mini': 0.64, 'anthropic/claude-3.7-sonnet': 0.60, 'transformer': 0.72}
NORMALIZED_WEIGHTS = [w / sum(EVALUATOR_WEIGHTS.values()) for w in EVALUATOR_WEIGHTS.values()]


class Model:
    def __init__(self, device='cpu'):
        self.device = device

        self.transformer = TransformerClassifier(vocab_size=tokenizer.vocab_size)
        self.transformer.load_state_dict(
            torch.load(Path(__file__).with_name('transformer.pth'), map_location=self.device)
        )
        self.transformer = self.transformer.to(self.device)
        self.transformer.eval()  # Set to evaluation mode

        self.evaluator_llms = [
            OpenRouter(model_name='openai/o4-mini', temperature=0),
            OpenRouter(model_name='anthropic/claude-3.7-sonnet', temperature=0),
        ]
        self.evaluator_chains = [
            evaluator_prompt | evaluator_llm | StrOutputParser() | JsonExtractor() | evaluator_parser
            for evaluator_llm in self.evaluator_llms
        ]

        self.explanation_llm = OpenRouter(model_name='openai/o4-mini', temperature=0)

        self.suggestions_llm = OpenRouter(model_name='openai/o4-mini', temperature=0)

        graph_builder = StateGraph(State)

        graph_builder.add_node('evaluators', self._evaluators)
        graph_builder.add_node('aggregator', self._aggregator)
        graph_builder.add_node('explanation_node', self._explanation)
        graph_builder.add_node('token_analysis', self._token_analysis)
        graph_builder.add_node('suggestions', self._suggestions)

        graph_builder.add_edge(START, 'evaluators')
        graph_builder.add_edge('evaluators', 'aggregator')
        graph_builder.add_edge('aggregator', 'explanation_node')
        graph_builder.add_edge('explanation_node', 'token_analysis')
        graph_builder.add_edge('token_analysis', 'suggestions')
        graph_builder.add_edge('suggestions', END)

        self.model = graph_builder.compile()

    def _clamp(self, n, min_value, max_value):
        return max(min_value, min(n, max_value))

    async def _evaluate_transformer(self, text: str) -> float:
        # Tokenize and prepare input
        encoding = tokenizer(
            text,
            add_special_tokens=True,
            max_length=MAX_LENGTH,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        # Get model prediction
        with torch.no_grad():
            outputs = self.transformer(input_ids, attention_mask)
            probs = F.softmax(outputs, dim=1)
            human_prob = probs[0][1].item()  # Probability of human class

        return human_prob

    async def _evaluate_chain(self, chain, text: str) -> float:
        try:
            result = await chain.ainvoke(text)
            score = result.score
            score = self._clamp(score, 0, 100)
            return score / 100
        except Exception as e:
            print(f'Error evaluating chain: {e}')
            return 0.5

    async def _evaluators(self, state: State) -> State:
        # Get scores from all evaluators
        llm_tasks = [self._evaluate_chain(chain, state['text']) for chain in self.evaluator_chains]
        llm_scores = await asyncio.gather(*llm_tasks)
        transformer_score = await self._evaluate_transformer(state['text'])

        # Combine all scores
        scores = llm_scores + [transformer_score]
        print('scores', scores)

        # Verify all scores are valid
        if any(score is None for score in scores):
            raise ValueError('One or more evaluators returned None score')

        return {'intermediate_scores': scores}

    def _aggregator(self, state: State) -> State:
        weighted_sum = sum(score * weight for score, weight in zip(state['intermediate_scores'], NORMALIZED_WEIGHTS))
        return {'score': weighted_sum}

    async def _explanation(self, state: State) -> State:
        prompt_values = {'text': state['text'], 'score': round(state['score'] * 100, 1)}

        tpl = explanation_prompt.format(**prompt_values)

        resp = await self.explanation_llm.ainvoke(tpl)
        text_resp = getattr(resp, 'content', str(resp))
        try:
            parsed = explanation_parser.parse(text_resp)
            return {'explanation': parsed.explanation}
        except Exception:
            return {'explanation': text_resp}

    async def _token_analysis(self, state: State) -> State:
        tokens = analyze_text_with_gradcam(state['text'])
        return {'tokens': tokens}

    async def _suggestions(self, state: State) -> State:
        tokens = [
            token for token in state['tokens']
            if len(token['token']) >= 3 and token['ai_prob'] > 0.4 and not set('#,.').intersection(token['token'])
        ]
        prompt_values = {
            'score': round(state['score'] * 100, 1),
            'explanation': state['explanation'],
            'tokens': tokens
        }
        tpl = suggestions_prompt.format(**prompt_values)
        resp = await self.suggestions_llm.ainvoke(tpl)
        text_resp = getattr(resp, 'content', str(resp))
        try:
            parsed = suggestions_parser.parse(text_resp)
            return {'examples': parsed.examples}
        except Exception:
            return {'examples': text_resp}

    async def ainvoke(self, text: str) -> Dict:
        return await self.model.ainvoke({'text': text})
