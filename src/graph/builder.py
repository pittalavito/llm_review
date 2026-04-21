import json

from langgraph.graph import END, StateGraph
from models.agent import AgentName, ReviewDecision
from agent.base import BaseAgent
from graph.state import ReviewState


class GraphBuilder:
    """Builds compiled LangGraph instances from a set of pre-configured agents.
    Agents are already injected with their ContextProvider — nodes just call agent.run().
    """

    @staticmethod
    def build(agents: dict[AgentName, BaseAgent]) -> StateGraph:
        soundness    = agents[AgentName.SOUNDNESS_REVIEWER]
        presentation = agents[AgentName.PRESENTATION_REVIEWER]
        contribution = agents[AgentName.CONTRIBUTION_REVIEWER]
        meta         = agents[AgentName.META_REVIEWER]
        refinement   = agents[AgentName.REFINEMENT_AGENT]

        graph = StateGraph(ReviewState)

        graph.add_node(AgentName.SOUNDNESS_REVIEWER,    GraphBuilder._reviewer_node(soundness))
        graph.add_node(AgentName.PRESENTATION_REVIEWER, GraphBuilder._reviewer_node(presentation))
        graph.add_node(AgentName.CONTRIBUTION_REVIEWER, GraphBuilder._reviewer_node(contribution))
        graph.add_node(AgentName.META_REVIEWER,         GraphBuilder._meta_node(meta))
        graph.add_node(AgentName.REFINEMENT_AGENT,      GraphBuilder._refinement_node(refinement))

        graph.set_entry_point(AgentName.SOUNDNESS_REVIEWER)
        graph.add_edge(AgentName.SOUNDNESS_REVIEWER,    AgentName.PRESENTATION_REVIEWER)
        graph.add_edge(AgentName.PRESENTATION_REVIEWER, AgentName.CONTRIBUTION_REVIEWER)
        graph.add_edge(AgentName.CONTRIBUTION_REVIEWER, AgentName.META_REVIEWER)

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
    def _reviewer_node(agent: BaseAgent):
        """Reviewer node: agent retrieves its own RAG context via ContextProvider."""

        def node(state: ReviewState) -> dict:
            paper_path = state.get("paper_path")
            message = "Analizza il paper e fornisci una review strutturata."
            revision_notes = state.get("revision_notes")
            if revision_notes:
                message += f"\n\nNote di revisione dal round precedente:\n{revision_notes}"
            review = agent.run(message, paper_path=paper_path)
            return {"reviews": [review]}

        return node

    @staticmethod
    def _meta_node(agent: BaseAgent):
        """Meta-reviewer node: aggregates last 3 reviews — no RAG needed."""

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
    def _refinement_node(agent: BaseAgent):
        """Refinement node: agent retrieves section context + receives meta-review."""

        def node(state: ReviewState) -> dict:
            paper_path = state.get("paper_path")
            meta_review = json.dumps(state.get("meta_review") or {}, ensure_ascii=False, indent=2)
            message = f"Meta-review ricevuta:\n{meta_review}"
            raw = agent.run(message, paper_path=paper_path)
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
