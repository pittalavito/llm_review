from typing import Any

from langgraph.graph import END, StateGraph

from agent.base_agent import BaseAgent
from schemas.controller.dev_controller import GraphCompileRequest
from schemas.enums import GraphNodeName
from schemas.graph.graph import GraphState
from service.llm_service import LlmService


class GraphFactory:
    @staticmethod
    def build(
        config: GraphCompileRequest,
        llm_service: LlmService,
    ) -> Any:
        graph = StateGraph(GraphState)

        methodology_reviewer_node = GraphNodeName.METHODOLOGY_REVIEWER
        methodology_reviewer_agent = llm_service.init_agent(
            config.methodology_reviewer_agent,
            config.methodology_reviewer_model,
            config.methodology_reviewer_temperature,
        )

        graph.add_node(methodology_reviewer_node, GraphFactory._make_node(methodology_reviewer_agent))
        graph.set_entry_point(methodology_reviewer_node)
        graph.add_edge(methodology_reviewer_node, END)
        return graph.compile()

    @staticmethod
    def _make_node(agent: BaseAgent):
        """Create a graph node function that runs the given agent."""

        def node(state: GraphState) -> dict:
            review = agent.run(state["paper"])
            return {
                "reviews": [review],
                "current_round": state["current_round"] + 1,
            }

        return node