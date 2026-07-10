from langgraph.graph import END, START, StateGraph

from domain.agent.base import BaseAgent
from domain.graph import edges
from domain.graph.nodes import area_chair_node, author_node, end_loop_conditional_edges, meta_node, reviewer_node, area_chair_conditional_edges
from domain.graph.state import ReviewState

from models.agent import AgentName

_REVIEWER_NODE = "reviewer_parallel_node"

_NODE_FACTORIES = {
    AgentName.REVIEWER_1: reviewer_node,
    AgentName.REVIEWER_2: reviewer_node,
    AgentName.REVIEWER_3: reviewer_node,
    AgentName.META_REVIEWER: meta_node,
    AgentName.AREA_CHAIR: area_chair_node,
    AgentName.AUTHOR_AGENT: author_node,
}

risp = {"accept": END, "revise": AgentName.AUTHOR_AGENT}
_AREA_CHAIR_CONDITIONAL_EDGE = AgentName.AREA_CHAIR, edges.ac_decision, risp


def build_graph(agents: dict[AgentName, BaseAgent]) -> StateGraph:
        graph = StateGraph(ReviewState)

        # Register agent nodes
        for name, factory in _NODE_FACTORIES.items():
            graph.add_node(name, factory(agents[name]))

        # Fan-out gateway for parallel reviewers
        graph.add_node(_REVIEWER_NODE, _passthrough)

        # START → fan-out → 3 reviewers in parallel
        graph.add_edge(START, _REVIEWER_NODE)
        graph.add_edge(_REVIEWER_NODE, AgentName.REVIEWER_1)
        graph.add_edge(_REVIEWER_NODE, AgentName.REVIEWER_2)
        graph.add_edge(_REVIEWER_NODE, AgentName.REVIEWER_3)

        # Fan-in: all reviewers converge on meta-reviewer
        graph.add_edge(AgentName.REVIEWER_1, AgentName.META_REVIEWER)
        graph.add_edge(AgentName.REVIEWER_2, AgentName.META_REVIEWER)
        graph.add_edge(AgentName.REVIEWER_3, AgentName.META_REVIEWER)

        graph.add_edge(AgentName.META_REVIEWER, AgentName.AREA_CHAIR)
        
        graph.add_conditional_edges(
            AgentName.AREA_CHAIR, 
            area_chair_conditional_edges,
            {"accept": END, "revise": AgentName.AUTHOR_AGENT}
        )

        graph.add_conditional_edges(
            AgentName.AUTHOR_AGENT, 
            end_loop_conditional_edges,
            {"loop": _REVIEWER_NODE, "end": END}
        )
        return graph



def _passthrough(_state: ReviewState) -> dict:
    """No-op node used as fan-out point for parallel reviewers."""
    return {}

