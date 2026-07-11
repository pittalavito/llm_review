from langgraph.graph import END, START, StateGraph

from domain.agent.base import BaseAgent
from domain.graph.state import ReviewState
from domain.graph.nodes import area_chair_node, author_node, meta_node, reviewer_node, area_chair_conditional_edges, end_loop_conditional_edges

from models.agent import AgentName
from models.graph import GraphNode, ReviewNode


def build_graph(agents: dict[AgentName, BaseAgent]) -> StateGraph:
    graph = StateGraph(ReviewState)
    
    _register_nodes(graph, agents)    
    _register_edges(graph)        
    _register_conditional_edges(graph)
    
    return graph


def _register_nodes(graph: StateGraph, agents: dict[AgentName, BaseAgent]) -> None:
    # Reviewer nodes
    graph.add_node(GraphNode.REVIEWER, {})  
    graph.add_node(ReviewNode.REVIEWER_1, reviewer_node(agents[AgentName.REVIEWER_1]))
    graph.add_node(ReviewNode.REVIEWER_2, reviewer_node(agents[AgentName.REVIEWER_2]))
    graph.add_node(ReviewNode.REVIEWER_3, reviewer_node(agents[AgentName.REVIEWER_3]))
    
    # Meta-reviewer node
    graph.add_node(GraphNode.META_REVIEWER, meta_node(agents[AgentName.META_REVIEWER]))
    
    # Area chair node
    graph.add_node(GraphNode.AREA_CHAIR, area_chair_node(agents[AgentName.AREA_CHAIR]))
    
    # Author node
    graph.add_node(GraphNode.AUTHOR_AGENT, author_node(agents[AgentName.AUTHOR_AGENT]))


def _register_edges(graph: StateGraph) -> None:
    # Reviewer edges
    graph.add_edge(START, GraphNode.REVIEWER)
    graph.add_edge(GraphNode.REVIEWER, ReviewNode.REVIEWER_1)
    graph.add_edge(GraphNode.REVIEWER, ReviewNode.REVIEWER_2)
    graph.add_edge(GraphNode.REVIEWER, ReviewNode.REVIEWER_3)
    
    # Meta-reviewer edges
    graph.add_edge(ReviewNode.REVIEWER_1, GraphNode.META_REVIEWER)
    graph.add_edge(ReviewNode.REVIEWER_2, GraphNode.META_REVIEWER)
    graph.add_edge(ReviewNode.REVIEWER_3, GraphNode.META_REVIEWER)
    
    # Area chair edges
    graph.add_edge(GraphNode.META_REVIEWER, GraphNode.AREA_CHAIR)


def _register_conditional_edges(graph: StateGraph) -> None:
    # Area chair conditional edges
    graph.add_conditional_edges(
        GraphNode.AREA_CHAIR, 
        area_chair_conditional_edges,
        {"accept": END, "revise": GraphNode.AUTHOR_AGENT}
    )
    
    # Author conditional edges
    graph.add_conditional_edges(
        GraphNode.AUTHOR_AGENT, 
        end_loop_conditional_edges,
        {"loop": GraphNode.REVIEWER, "end": END}
    )