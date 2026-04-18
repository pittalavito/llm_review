import asyncio
from typing import Any

from factory.graph_factory import GraphFactory
from schemas.controller.dev_controller import GraphCompileRequest
from schemas.graph.graph import GraphState
from service.llm_service import LlmService
from service.retrieval_service import RetrievalService


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
            self.graph = GraphFactory.build(
                config=config,
                llm_service=llm_service,
            )
                        
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

    def invoke_from_file(
        self,
        retrieval_service: RetrievalService,
        paper_path: str,
        top_k: int | None = None,
        force_reindex: bool = False,
    ) -> tuple[dict, dict]:
        """Retrieve context from a file and invoke the graph."""
        retrieval_result = retrieval_service.retrieve_for_methodology_review(
            paper_path=paper_path,
            top_k=top_k,
            force_reindex=force_reindex,
        )
        context = retrieval_result["context"]
        metadata = retrieval_result["metadata"]

        result = self.invoke({"paper": context})
        return result, metadata
    
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
