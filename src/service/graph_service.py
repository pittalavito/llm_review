import asyncio
from typing import Any

from langgraph.graph import END, StateGraph

from agent.base_agent import BaseAgent
from schemas.controller import GraphCompileRequest
from schemas.enums import GraphNodeName
from schemas.graph import GraphState
from service.llm_service import LlmService


class GraphService:
    
    def __init__(self):
        self.graph_config: GraphCompileRequest | None = None
        self.graph: Any = None
        self.graph_lock = asyncio.Lock()
    
    def get_config(self) -> GraphCompileRequest | None:
        """Get the current graph configuration."""
        return self.graph_config
    
    async def compile_graph(self, config: GraphCompileRequest, llm_service: LlmService):
        """Compile the graph with the given configuration and store it in memory."""
        async with self.graph_lock:
            self.graph_config = config
            self.graph = self._compile(llm_service)
                        
    def invoke(self, input_data: dict) -> dict:
        """Invoke the graph synchronously with the given input data."""
        if self.graph is None:
            raise ValueError("Graph is not compiled yet.")
        initial_state = self._build_initial_state(input_data["paper"])
        return self.graph.invoke(initial_state)
    
    async def invoke_async(self, input_data: dict) -> dict:
        """Invoke the graph asynchronously with the given input data."""
        if self.graph is None:
            raise ValueError("Graph is not compiled yet.")
            
        initial_state = self._build_initial_state(input_data["paper"])
        return await self.graph.ainvoke(initial_state)
    
    def _make_node(self, agent: BaseAgent):
        """Create a graph node function that runs the given agent."""
        def node(state: GraphState) -> dict:
            review = agent.run(state["paper"])
            return {
                "reviews": [review],
                "current_round": state["current_round"] + 1,
            }
        return node

    def _build_initial_state(self, paper: str) -> GraphState:
        if self.graph_config is None:
            raise ValueError("Graph is not compiled yet.")

        return {
            "paper": paper,
            "messages": [],
            "reviews": [],
            "current_round": 0,
            "max_rounds": self.graph_config.max_iterations,
        }
    
    def _compile(self, llm_service: LlmService) -> StateGraph:
        """Compile the graph based on the current configuration and LLM service."""
        config: GraphCompileRequest = self.graph_config
        graph = StateGraph(GraphState)
        
        methodology_reviewer_node = GraphNodeName.METHODOLOGY_REVIEWER
        methodology_reviewer_agent = llm_service.init_agent(
            config.methodology_reviewer_agent,
            config.methodology_reviewer_model,
            config.methodology_reviewer_temperature,
        )
        
        graph.add_node(methodology_reviewer_node, self._make_node(methodology_reviewer_agent))
        graph.set_entry_point(methodology_reviewer_node)
        graph.add_edge(methodology_reviewer_node, END)
        return graph.compile()