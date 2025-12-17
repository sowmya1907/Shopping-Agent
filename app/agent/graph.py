from langgraph.graph import StateGraph
from .state import AgentState
from .nodes import price_search_node, PLATFORMS

def build_graph():
    graph = StateGraph(AgentState)

    for platform in PLATFORMS.keys():
        graph.add_node(
            platform,
            lambda state, p=platform: price_search_node(state, p)
        )

    graph.set_entry_point("Amazon")

    platforms = list(PLATFORMS.keys())
    for i in range(len(platforms) - 1):
        graph.add_edge(platforms[i], platforms[i + 1])

    graph.set_finish_point(platforms[-1])

    return graph.compile()
