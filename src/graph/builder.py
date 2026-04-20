import json

from langgraph.graph import END, StateGraph
from models.agent import AgentName, ReviewDecision
from agent.base import BaseAgent
from graph.state import ReviewState
from retrieval.protocols import RetrievalContextProvider


class GraphBuilder:
    """Builds compiled LangGraph instances from a configuration."""

    @staticmethod
    def build(agents: dict[AgentName, BaseAgent], retrieval_service: RetrievalContextProvider) -> StateGraph:
        soundness    = agents[AgentName.SOUNDNESS_REVIEWER]
        presentation = agents[AgentName.PRESENTATION_REVIEWER]
        contribution = agents[AgentName.CONTRIBUTION_REVIEWER]
        meta         = agents[AgentName.META_REVIEWER]
        refinement   = agents[AgentName.REFINEMENT_AGENT]

        graph = StateGraph(ReviewState)

        # NODES
        graph.add_node(
            AgentName.SOUNDNESS_REVIEWER, 
            GraphBuilder._reviewer_node(soundness, retrieval_service)
        )
        graph.add_node(
            AgentName.PRESENTATION_REVIEWER, 
            GraphBuilder._reviewer_node(presentation, retrieval_service)
        )
        graph.add_node(
            AgentName.CONTRIBUTION_REVIEWER, 
            GraphBuilder._reviewer_node(contribution, retrieval_service)
        )
        graph.add_node(
            AgentName.META_REVIEWER, 
            GraphBuilder._meta_node(meta)
        )
        graph.add_node(
            AgentName.REFINEMENT_AGENT,
            GraphBuilder._refinement_node(refinement, retrieval_service)
        )

        # EDGES
        graph.set_entry_point(AgentName.SOUNDNESS_REVIEWER)
        graph.add_edge(AgentName.SOUNDNESS_REVIEWER, AgentName.PRESENTATION_REVIEWER)
        graph.add_edge(AgentName.PRESENTATION_REVIEWER, AgentName.CONTRIBUTION_REVIEWER)
        graph.add_edge(AgentName.CONTRIBUTION_REVIEWER, AgentName.META_REVIEWER)

        # CONDITIONAL EDGES
        graph.add_conditional_edges(
            AgentName.META_REVIEWER,
            GraphBuilder._meta_decision,
            {"accept": END, "revise": AgentName.REFINEMENT_AGENT},
        )
        graph.add_conditional_edges(
            AgentName.REFINEMENT_AGENT,
            GraphBuilder._should_loop,
            {"loop": AgentName.SOUNDNESS_REVIEWER, "end": END},
        )

        return graph

    # ---------------------------------------------------------------------------
    # Node builders
    # ---------------------------------------------------------------------------

    @staticmethod
    def _reviewer_node(agent: BaseAgent, retrieval_service: RetrievalContextProvider):
        """Nodo reviewer: recupera contesto via RAG e invoca l'agente."""

        def node(state: ReviewState) -> dict:
            paper_path = state["paper_path"]
            result = retrieval_service.retrieve_context(
                paper_path=paper_path,
                top_k=state.get("rag_top_k"),
                force_reindex=False,
                query=agent.RAG_QUERY,
            )
            message = result["context"]

            revision_notes = state.get("revision_notes")
            if revision_notes:
                message = f"{message}\n\n--- Note di revisione dal round precedente ---\n{revision_notes}"

            review = agent.run(message)
            return {"reviews": [review]}

        return node

    @staticmethod
    def _meta_node(agent: BaseAgent):
        """Nodo meta-reviewer: aggrega le ultime 3 review del round corrente."""

        def node(state: ReviewState) -> dict:
            current_reviews = [json.loads(r) for r in state["reviews"][-3:]]
            reviews_text = json.dumps(current_reviews, ensure_ascii=False, indent=2)
            raw = agent.run(reviews_text)
            payload = json.loads(raw).get("payload", {})
            return {
                "meta_review": payload,
                "decision": payload.get("decision"),
                "current_round": state["current_round"] + 1,
            }

        return node

    @staticmethod
    def _refinement_node(agent: BaseAgent, retrieval_service: RetrievalContextProvider):
        """Nodo refinement: produce note di revisione da contesto RAG + meta-review."""

        def node(state: ReviewState) -> dict:
            paper_path = state["paper_path"]
            rag_result = retrieval_service.retrieve_context(
                paper_path=paper_path,
                top_k=state.get("rag_top_k"),
                force_reindex=False,
                query="main contributions methodology results limitations",
            )
            context = json.dumps(
                {"paper_excerpt": rag_result["context"][:1_000], "meta_review": state.get("meta_review") or {}},
                ensure_ascii=False,
                indent=2,
            )
            raw = agent.run(context)
            payload = json.loads(raw).get("payload", {})
            return {"revision_notes": payload.get("revision_summary", "")}

        return node

    # ---------------------------------------------------------------------------
    # Conditional edge functions
    # ---------------------------------------------------------------------------

    @staticmethod
    def _meta_decision(state: ReviewState) -> str:
        return "accept" if state.get("decision") == ReviewDecision.ACCEPT else "revise"

    @staticmethod
    def _should_loop(state: ReviewState) -> str:
        return "end" if state["current_round"] >= state["max_rounds"] else "loop"
