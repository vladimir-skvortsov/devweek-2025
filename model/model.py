import asyncio
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

load_dotenv()


class EvaluatorSchema(BaseModel):
    score: int = Field(description='Given the text, return score from 0 to 100 indicating how human-like the text is')


class ExplanationSchema(BaseModel):
    explanation: str = Field(..., description='Detailed analysis of why the detector scored this way')


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


class State(TypedDict):
    text: str
    intermediate_scores: list[float]
    score: float
    explanation: str


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

        graph_builder = StateGraph(State)

        graph_builder.add_node('evaluators', self._evaluators)
        graph_builder.add_node('aggregator', self._aggregator)
        graph_builder.add_node('explanation_node', self._explanation)

        graph_builder.add_edge(START, 'evaluators')
        graph_builder.add_edge('evaluators', 'aggregator')
        graph_builder.add_edge('aggregator', 'explanation_node')
        graph_builder.add_edge('explanation_node', END)

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

    async def ainvoke(self, text: str) -> float:
        init_state = {'text': text}
        return await self.model.ainvoke(init_state)
