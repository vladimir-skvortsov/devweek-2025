from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio

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
            OpenRouter(model_name='anthropic/claude-3.7-sonnet', temperature=0),
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

    async def _evaluate_chain(self, chain, text):
        try:
            result = await chain.ainvoke({'text': text})
            score = result.score
            score = self._clamp(score, 0, 100)
            return score / 100
        except:
            return None

    async def _evaluators(self, state: State) -> State:
        tasks = [self._evaluate_chain(chain, state['text']) for chain in self.evaluator_chains]
        scores = await asyncio.gather(*tasks)
        scores = [score for score in scores if score is not None]

        return {'intermediate_scores': scores}

    def _aggregator(self, state: State) -> State:
        score = sum(state['intermediate_scores']) / len(state['intermediate_scores'])
        return {'score': score}

    async def ainvoke(self, text: str) -> float:
        return (await self.model.ainvoke({'text': text}))['score']
