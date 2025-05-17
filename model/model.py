from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    text: str
    score: float


graph_builder = StateGraph(State)


def judge(state: State):
    return {'score': 0.8}


graph_builder.add_node('judge', judge)

graph_builder.add_edge(START, 'judge')
graph_builder.add_edge('judge', END)

model = graph_builder.compile()
