from langgraph.graph import END, START, StateGraph

from agent.base import BaseAgent
from graph import edges
from graph.nodes.area_chair import area_chair_node
from graph.nodes.author import author_node
from graph.nodes.meta import meta_node
from graph.nodes.reviewer import reviewer_node
from graph.state import ReviewState
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

def _passthrough(_state: ReviewState) -> dict:
    """No-op node used as fan-out point for parallel reviewers."""
    return {}


class GraphBuilder:

    @staticmethod
    def build(agents: dict[AgentName, BaseAgent]) -> StateGraph:
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

        # Meta-reviewer → Area Chair → decision
        graph.add_edge(AgentName.META_REVIEWER, AgentName.AREA_CHAIR)
        graph.add_conditional_edges(
            AgentName.AREA_CHAIR, edges.ac_decision,
            {"accept": END, "revise": AgentName.AUTHOR_AGENT},
        )

        # Author agent → loop back to parallel reviewers or end
        graph.add_conditional_edges(
            AgentName.AUTHOR_AGENT, edges.should_loop,
            {"loop": _REVIEWER_NODE, "end": END},
        )
        return graph
