"""
SqlResultRepository tests:
  - build_run_id format
  - save -> get round-trip fidelity (incl. double-encoded reviews)
  - round-trip of a real legacy JSON file
  - list ordering and summary fields
  - missing run -> ValueError
  - agent-run filtering in SQL
  - upsert semantics (same run_id replaces, no duplicated children)
  - extracted analytics columns and normalized config rows
"""
import json
import re

import pytest
from sqlalchemy import text

from config import Config, RESULTS_DIR
from db.engine import create_db_engine, init_db
from db.sql_result_repository import SqlResultRepository
from models.agent import AgentName
from models.run_record import RunRecord

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine(tmp_path):
    config = Config(database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    engine = create_db_engine(config)
    init_db(engine)
    return engine


@pytest.fixture()
def repo(engine):
    return SqlResultRepository(engine)


def make_record(run_id: str = "2026-07-05T10-00-00_test_paper") -> RunRecord:
    reviewer_payload = {
        "summary": "Solid work",
        "significance_and_novelty": "Novel enough",
        "reasons_for_acceptance": ["clear method"],
        "reasons_for_rejection": [],
        "suggestions": ["add ablations"],
        "rating": 7,
        "confidence": 4,
    }
    return RunRecord(
        run_id=run_id,
        timestamp="2026-07-05T10:00:00.000000+00:00",
        paper_path="test_paper.pdf",
        run_description="unit-test run",
        decision="accept",
        total_rounds=1,
        reviews=[json.dumps(reviewer_payload)],  # double-encoded, as produced by the graph
        meta_review={
            "summary": "Agreement among reviewers",
            "key_points": ["sound"],
            "overall_score": 8,
            "recommendation": "accept",
        },
        area_chair_response={
            "summary": "Accept",
            "justification": "Consensus",
            "decision": "accept",
            "confidence": 5,
        },
        author_response=None,
        retrieval_metadata={"paper_path": "test_paper.pdf", "index_status": "reused"},
        graph_config={
            "agents": [
                {
                    "agent_name": "reviewer_1",
                    "model": "mock",
                    "temperature": 0.4,
                    "reviewer_persona": {
                        "commitment": "responsible",
                        "intention": "benign",
                        "knowledgeability": "knowledgeable",
                        "focus": "soundness",
                    },
                    "area_chair_style": None,
                },
                {
                    "agent_name": "area_chair",
                    "model": "mock",
                    "temperature": 0.2,
                    "reviewer_persona": None,
                    "area_chair_style": "inclusive",
                },
            ],
            "max_rounds": 2,
        },
        agent_runs=[
            {
                "agent": "reviewer_1",
                "round": 0,
                "input_message": "Review the paper.",
                "context_used": "chunk-1",
                "response_payload": reviewer_payload,
                "prompt_trace": {"template": "t", "rendered": "r"},
                "runtime_trace": {
                    "llm": "mock",
                    "metrics": {"latency_ms": 123.4},
                    "provider_usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
            {
                "agent": "meta_reviewer",
                "round": 0,
                "input_message": "Synthesize.",
                "context_used": None,
                "response_payload": {
                    "summary": "s",
                    "key_points": [],
                    "overall_score": 8,
                    "recommendation": "accept",
                },
            },
            {
                "agent": "area_chair",
                "round": 0,
                "input_message": "Decide.",
                "context_used": None,
                "response_payload": {
                    "summary": "s",
                    "justification": "j",
                    "decision": "accept",
                    "confidence": 5,
                },
            },
        ],
    )


# ---------------------------------------------------------------------------
# build_run_id
# ---------------------------------------------------------------------------

class TestBuildRunId:

    def test_format(self):
        run_id = SqlResultRepository.build_run_id("papers/My Paper (v2).pdf")
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}_My_Paper__v2_$", run_id)

    def test_stem_truncated_to_40_chars(self):
        run_id = SqlResultRepository.build_run_id("x" * 100 + ".pdf")
        stem = run_id.split("_", 1)[1] if "_" in run_id else ""
        assert len(run_id.split("T", 1)[1].split("_", 1)[1]) <= 40 or len(stem) <= 41


# ---------------------------------------------------------------------------
# save / get round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:

    def test_save_returns_run_id(self, repo):
        record = make_record()
        assert repo.save(record) == record.run_id

    def test_get_returns_identical_record(self, repo):
        record = make_record()
        repo.save(record)
        loaded = repo.get(record.run_id)
        assert loaded.model_dump() == record.model_dump()

    def test_reviews_stay_double_encoded(self, repo):
        record = make_record()
        repo.save(record)
        loaded = repo.get(record.run_id)
        assert isinstance(loaded.reviews[0], str)
        assert json.loads(loaded.reviews[0])["rating"] == 7

    def test_legacy_file_round_trip(self, repo):
        legacy_files = sorted(RESULTS_DIR.glob("*.json"))
        if not legacy_files:
            pytest.skip("no legacy result files available")
        data = json.loads(legacy_files[0].read_text(encoding="utf-8"))
        record = RunRecord.model_validate(data)
        repo.save(record)
        loaded = repo.get(record.run_id)
        assert loaded.model_dump() == record.model_dump()

    def test_get_missing_raises_value_error(self, repo):
        with pytest.raises(ValueError):
            repo.get("2099-01-01T00-00-00_missing")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestList:

    def test_ordering_most_recent_first(self, repo):
        repo.save(make_record("2026-01-01T00-00-00_old"))
        repo.save(make_record("2026-06-01T00-00-00_new"))
        summaries = repo.list()
        assert [s.run_id for s in summaries] == [
            "2026-06-01T00-00-00_new",
            "2026-01-01T00-00-00_old",
        ]

    def test_summary_fields(self, repo):
        record = make_record()
        repo.save(record)
        summary = repo.list()[0]
        assert summary.paper_path == record.paper_path
        assert summary.run_description == record.run_description
        assert summary.decision == record.decision
        assert summary.total_rounds == record.total_rounds
        assert summary.timestamp == record.timestamp


# ---------------------------------------------------------------------------
# get_agent_runs
# ---------------------------------------------------------------------------

class TestGetAgentRuns:

    def test_no_filter_returns_all_in_order(self, repo):
        record = make_record()
        repo.save(record)
        runs = repo.get_agent_runs(record.run_id)
        assert [r.agent for r in runs] == [
            AgentName.REVIEWER_1, AgentName.META_REVIEWER, AgentName.AREA_CHAIR,
        ]

    def test_filter_by_agent(self, repo):
        record = make_record()
        repo.save(record)
        runs = repo.get_agent_runs(record.run_id, agent_name=AgentName.META_REVIEWER)
        assert len(runs) == 1
        assert runs[0].agent == AgentName.META_REVIEWER

    def test_filter_by_round(self, repo):
        record = make_record()
        repo.save(record)
        assert len(repo.get_agent_runs(record.run_id, round_index=0)) == 3
        assert repo.get_agent_runs(record.run_id, round_index=1) == []

    def test_missing_run_raises_value_error(self, repo):
        with pytest.raises(ValueError):
            repo.get_agent_runs("2099-01-01T00-00-00_missing")


# ---------------------------------------------------------------------------
# upsert semantics
# ---------------------------------------------------------------------------

class TestUpsert:

    def test_same_run_id_replaces_without_duplicating_children(self, repo, engine):
        record = make_record()
        repo.save(record)
        updated = record.model_copy(update={"run_description": "second save"})
        repo.save(updated)

        assert repo.get(record.run_id).run_description == "second save"
        with engine.connect() as conn:
            agent_rows = conn.execute(
                text("SELECT COUNT(*) FROM agent_run WHERE run_id = :r"), {"r": record.run_id}
            ).scalar()
            config_rows = conn.execute(
                text("SELECT COUNT(*) FROM run_agent_config WHERE run_id = :r"),
                {"r": record.run_id},
            ).scalar()
        assert agent_rows == len(record.agent_runs)
        assert config_rows == len(record.graph_config["agents"])


# ---------------------------------------------------------------------------
# extracted analytics columns
# ---------------------------------------------------------------------------

class TestAnalyticsColumns:

    def test_reviewer_rating_confidence_and_tokens(self, repo, engine):
        repo.save(make_record())
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT rating, confidence, latency_ms, input_tokens, output_tokens, total_tokens"
                " FROM agent_run WHERE agent = 'reviewer_1'"
            )).one()
        assert tuple(row) == (7, 4, 123.4, 100, 50, 150)

    def test_meta_and_area_chair_decisions(self, repo, engine):
        repo.save(make_record())
        with engine.connect() as conn:
            meta = conn.execute(text(
                "SELECT overall_score, decision FROM agent_run WHERE agent = 'meta_reviewer'"
            )).one()
            chair = conn.execute(text(
                "SELECT confidence, decision FROM agent_run WHERE agent = 'area_chair'"
            )).one()
        assert tuple(meta) == (8, "accept")
        assert tuple(chair) == (5, "accept")

    def test_run_denormalized_columns(self, repo, engine):
        repo.save(make_record())
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT max_rounds, meta_overall_score FROM run"
            )).one()
        assert tuple(row) == (2, 8)

    def test_run_agent_config_rows(self, repo, engine):
        repo.save(make_record())
        with engine.connect() as conn:
            reviewer = conn.execute(text(
                "SELECT model, temperature, persona_focus, area_chair_style"
                " FROM run_agent_config WHERE agent_name = 'reviewer_1'"
            )).one()
            chair = conn.execute(text(
                "SELECT persona_focus, area_chair_style"
                " FROM run_agent_config WHERE agent_name = 'area_chair'"
            )).one()
        assert tuple(reviewer) == ("mock", 0.4, "soundness", None)
        assert tuple(chair) == (None, "inclusive")

    def test_out_of_range_rating_stored_as_null(self, repo, engine):
        record = make_record()
        record.agent_runs[0].response_payload = dict(
            record.agent_runs[0].response_payload, rating=0
        )
        repo.save(record)
        with engine.connect() as conn:
            rating = conn.execute(text(
                "SELECT rating FROM agent_run WHERE agent = 'reviewer_1'"
            )).scalar()
        assert rating is None
