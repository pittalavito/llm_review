import json

from langgraph.graph import END, StateGraph
from models.agent import AgentName, ReviewDecision
from models.run_record import AgentRun
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
        author       = agents[AgentName.AUTHOR_AGENT]

        graph = StateGraph(ReviewState)

        graph.add_node(AgentName.SOUNDNESS_REVIEWER,    GraphBuilder._reviewer_node(soundness))
        graph.add_node(AgentName.PRESENTATION_REVIEWER, GraphBuilder._reviewer_node(presentation))
        graph.add_node(AgentName.CONTRIBUTION_REVIEWER, GraphBuilder._reviewer_node(contribution))
        graph.add_node(AgentName.META_REVIEWER,         GraphBuilder._meta_node(meta))
        graph.add_node(AgentName.AUTHOR_AGENT,          GraphBuilder._author_node(author))

        graph.set_entry_point(AgentName.SOUNDNESS_REVIEWER)
        graph.add_edge(AgentName.SOUNDNESS_REVIEWER,    AgentName.PRESENTATION_REVIEWER)
        graph.add_edge(AgentName.PRESENTATION_REVIEWER, AgentName.CONTRIBUTION_REVIEWER)
        graph.add_edge(AgentName.CONTRIBUTION_REVIEWER, AgentName.META_REVIEWER)

        graph.add_conditional_edges(
            AgentName.META_REVIEWER,
            GraphBuilder._meta_decision,
            {"accept": END, "revise": AgentName.AUTHOR_AGENT},
        )
        graph.add_conditional_edges(
            AgentName.AUTHOR_AGENT,
            GraphBuilder._should_loop,
            {"loop": AgentName.SOUNDNESS_REVIEWER, "end": END},
        )

        return graph

    # ---------------------------------------------------------------------------
    # Node builders
    # ---------------------------------------------------------------------------

    @staticmethod
    def _reviewer_node(agent: BaseAgent):
        def node(state: ReviewState) -> dict:
            paper_path = state.get("paper_path")
            message = "Analyze the paper and provide a structured review."

            author_response = state.get("author_response")
            if author_response:
                rebuttal = author_response.get("rebuttal", "")
                revised_sections = author_response.get("revised_sections", {})
                if rebuttal:
                    message += f"\n\nAuthor rebuttal from the previous round:\n{rebuttal}"
                if revised_sections:
                    if isinstance(revised_sections, list):
                        sections_text = "\n\n".join(
                            f"[Revised {s['section_name'].upper()}]\n{s['content']}"
                            for s in revised_sections
                        )
                    else:
                        sections_text = "\n\n".join(
                            f"[Revised {section.upper()}]\n{text}"
                            for section, text in revised_sections.items()
                        )
                    message += f"\n\nRevised paper sections submitted by the author:\n{sections_text}"

            response = agent.run(message, paper_path=paper_path)
            agent_run = AgentRun(
                agent=response.agent,
                round=state["current_round"],
                input_message=response.input_message or message,
                context_used=response.context_used,
                response_payload=response.payload.model_dump(),
            )
            return {"reviews": [response.to_json()], "agent_runs": [agent_run.model_dump()]}

        return node

    @staticmethod
    def _meta_node(agent: BaseAgent):
        def node(state: ReviewState) -> dict:
            current_reviews = [json.loads(r) for r in state["reviews"][-3:]]
            reviews_text = json.dumps(current_reviews, ensure_ascii=False, indent=2)

            response = agent.run(reviews_text)
            payload = response.payload  # MetaReviewResponse — typed

            agent_run = AgentRun(
                agent=response.agent,
                round=state["current_round"],
                input_message=response.input_message or reviews_text,
                context_used=response.context_used,
                response_payload=payload.model_dump(),
            )
            return {
                "meta_review": payload.model_dump(),
                "decision": payload.decision,
                "current_round": state["current_round"] + 1,
                "agent_runs": [agent_run.model_dump()],
            }

        return node

    @staticmethod
    def _author_node(agent: BaseAgent):
        def node(state: ReviewState) -> dict:
            paper_path = state.get("paper_path")
            meta_review = json.dumps(state.get("meta_review") or {}, ensure_ascii=False, indent=2)
            reviews = [json.loads(r) for r in state["reviews"][-3:]]
            reviews_text = json.dumps(reviews, ensure_ascii=False, indent=2)
            message = (
                f"You have received the following peer reviews:\n{reviews_text}\n\n"
                f"The meta-reviewer's decision:\n{meta_review}\n\n"
                "Write your rebuttal and provide revised versions of the sections that need improvement."
            )

            response = agent.run(message, paper_path=paper_path)
            payload = response.payload  # AuthorResponse — typed

            agent_run = AgentRun(
                agent=response.agent,
                round=state["current_round"] - 1,
                input_message=response.input_message or message,
                context_used=response.context_used,
                response_payload=payload.model_dump(),
            )
            return {
                "author_response": payload.model_dump(),
                "revised_sections": {s.section_name: s.content for s in payload.revised_sections},
                "agent_runs": [agent_run.model_dump()],
            }

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
