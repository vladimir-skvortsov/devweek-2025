from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from model.utils.JsonExtractor import JsonExtractor
from model.utils.OpenRouter import OpenRouter

load_dotenv()


class EvaluatorSchema(BaseModel):
    score: int = Field(description='Given the text, return score from 0 to 100 indicating how human-like the text is')


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


class State(TypedDict):
    text: str
    intermediate_scores: list[float]
    score: float


class Model:
    def __init__(self):
        self.evaluator_llms = [
            OpenRouter(model_name='openai/gpt-4.1', temperature=0),
            # OpenRouter(model_name='meta-llama/llama-3.3-8b-instruct:free', temperature=0),
        ]
        self.evaluator_chains = [
            evaluator_prompt | evaluator_llm | StrOutputParser() | JsonExtractor() | evaluator_parser
            for evaluator_llm in self.evaluator_llms
        ]

        graph_builder = StateGraph(State)

        graph_builder.add_node('evaluators', self._evaluators)
        graph_builder.add_node('aggregator', self._aggregator)

        graph_builder.add_edge(START, 'evaluators')
        graph_builder.add_edge('evaluators', 'aggregator')
        graph_builder.add_edge('aggregator', END)

        self.model = graph_builder.compile()

    def _clamp(self, n, min_value, max_value):
        return max(min_value, min(n, max_value))

    def _evaluators(self, state: State) -> State:
        scores = []

        for chain in self.evaluator_chains:
            try:
                score = chain.invoke({'text': state['text']}).score
                score = self._clamp(score, 0, 100)
                score /= 100
                scores.append(score)
            except:
                pass

        return {'intermediate_scores': scores}

    def _aggregator(self, state: State) -> State:
        score = sum(state['intermediate_scores']) / len(state['intermediate_scores'])
        return {'score': score}

    def invoke(self, text: str) -> float:
        return self.model.invoke({'text': text})['score']
