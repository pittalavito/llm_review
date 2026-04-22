"""
Integration tests:
  - Config defaults
  - Container wiring
  - AgentService client factory
  - RetrievalService (index, retrieve, validate)
"""
import sys
import copy
import pytest

sys.path.insert(0, "src")

from config import Config
from container import Container
from models.agent import AgentName, LlmModelName

PAPER_PATH = "2566_Robust_agents_learn_causa.pdf"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def config():
    return Config()


@pytest.fixture(scope="module")
def container(config):
    c = Container(config)
    c.compile_graph()
    return c


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:

    def test_default_app_name(self, config):
        assert config.app_name == "llm-review"

    def test_default_rag_chunk_size(self, config):
        assert config.rag_chunk_size > 0

    def test_default_rag_chunk_overlap_less_than_chunk_size(self, config):
        assert config.rag_chunk_overlap < config.rag_chunk_size

    def test_default_top_k(self, config):
        assert config.rag_top_k_default > 0

    def test_ollama_url_set(self, config):
        assert config.ollama_url.startswith("http")

    def test_strategy_version_set(self, config):
        assert config.rag_strategy_version != ""


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

class TestContainer:

    def test_health_check_returns_ok(self, container):
        assert container.health_check()["status"] == "ok"

    def test_health_check_returns_version(self, container):
        assert "version" in container.health_check()

    def test_list_papers_returns_list(self, container):
        assert isinstance(container.list_papers_path(), list)

    def test_list_indexed_papers_returns_list(self, container):
        assert isinstance(container.list_indexed_papers(), list)

    def test_build_agent_prompt_returns_dict(self, container):
        result = container.build_agent_prompt(AgentName.SOUNDNESS_REVIEWER, "test message")
        assert "system_prompt" in result
        assert "full_prompt" in result

    def test_test_agent_with_mock_returns_response(self, container):
        assert container.test_agent(
            AgentName.SOUNDNESS_REVIEWER, LlmModelName.MOCK, 0.0, "review this paper"
        ) is not None

    def test_compile_graph_is_idempotent(self, container):
        container.compile_graph()


# ---------------------------------------------------------------------------
# AgentService — client factory
# ---------------------------------------------------------------------------

class TestAgentServiceClientFactory:

    def test_mock_client_created(self, config):
        from service.agent_service import AgentService
        from client.mock_chat import MockChatModel
        svc = AgentService(config)
        assert isinstance(svc.init_client(LlmModelName.MOCK, 0.0), MockChatModel)

    def test_client_cached_on_second_call(self, config):
        from service.agent_service import AgentService
        svc = AgentService(config)
        assert svc.init_client(LlmModelName.MOCK, 0.0) is svc.init_client(LlmModelName.MOCK, 0.0)

    def test_openai_raises_without_key(self):
        from service.agent_service import AgentService
        svc = AgentService(Config(openai_api_key=None))
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            svc.init_client(LlmModelName.OPENAI_GPT4O, 0.0)

    def test_anthropic_raises_without_key(self):
        from service.agent_service import AgentService
        svc = AgentService(Config(anthropic_api_key=None))
        with pytest.raises(ValueError, match="ANTHROPIC"):
            svc.init_client(LlmModelName.ANTHROPIC_CLAUDE_SONNET, 0.0)

    def test_get_agent_class_soundness(self):
        from service.agent_service import AgentService
        from agent.impl.soundness_reviewer import SoundnessReviewerAgent
        assert AgentService.get_agent_class(AgentName.SOUNDNESS_REVIEWER) is SoundnessReviewerAgent

    def test_get_agent_class_unknown_raises(self):
        from service.agent_service import AgentService
        with pytest.raises(ValueError):
            AgentService.get_agent_class("nonexistent_agent")

    def test_run_agent_returns_agent_response(self, config):
        from service.agent_service import AgentService
        from models.agent import AgentResponse
        svc = AgentService(config)
        assert isinstance(
            svc.run_agent(AgentName.SOUNDNESS_REVIEWER, LlmModelName.MOCK, 0.0, "analyse this"),
            AgentResponse,
        )


# ---------------------------------------------------------------------------
# RetrievalService
# ---------------------------------------------------------------------------

class TestRetrievalService:

    @pytest.fixture(scope="class")
    def svc(self):
        from service.retrieval_service import RetrievalService
        return RetrievalService(Config())

    # -- list_papers ----------------------------------------------------------

    def test_list_papers_contains_known_paper(self, svc):
        assert PAPER_PATH in svc.list_papers()

    # -- index_paper ----------------------------------------------------------

    def test_index_paper_builds_index(self, svc):
        meta = svc.index_paper(PAPER_PATH, force_reindex=True)
        assert meta.paper_path == PAPER_PATH
        assert meta.index_status == "rebuilt"
        assert meta.chunk_count_total > 0

    def test_index_paper_reuses_index(self, svc):
        svc.index_paper(PAPER_PATH, force_reindex=True)
        assert svc.index_paper(PAPER_PATH, force_reindex=False).index_status == "reused"

    def test_index_paper_invalid_path_raises(self, svc):
        with pytest.raises((ValueError, FileNotFoundError)):
            svc.index_paper("nonexistent/paper.pdf")

    # -- retrieve_for_agent ---------------------------------------------------

    def test_retrieve_for_agent_returns_string(self, svc):
        svc.index_paper(PAPER_PATH, force_reindex=True)
        ctx = svc.retrieve_for_agent(PAPER_PATH, query="methodology experiments")
        assert isinstance(ctx, str) and len(ctx) > 0

    def test_retrieve_for_agent_with_sections(self, svc):
        ctx = svc.retrieve_for_agent(
            PAPER_PATH,
            query="experimental results",
            sections=["methods", "experiments", "results"],
        )
        assert isinstance(ctx, str)

    def test_retrieve_for_agent_rebuilds_if_invalid(self, svc, monkeypatch):
        monkeypatch.setattr(svc._index_repository, "load", lambda _: None)
        assert isinstance(svc.retrieve_for_agent(PAPER_PATH, query="model architecture"), str)

    # -- get_indexed_paper ----------------------------------------------------

    def test_get_indexed_paper_returns_info(self, svc):
        svc.index_paper(PAPER_PATH, force_reindex=True)
        info = svc.get_indexed_paper(PAPER_PATH)
        assert info.paper_path == PAPER_PATH and info.chunk_count > 0

    def test_get_indexed_paper_not_indexed_raises(self, svc, monkeypatch):
        monkeypatch.setattr(svc._index_repository, "load", lambda _: None)
        with pytest.raises(ValueError, match="No index found"):
            svc.get_indexed_paper(PAPER_PATH)

    # -- list_indexed_papers --------------------------------------------------

    def test_list_indexed_papers_returns_list(self, svc):
        svc.index_paper(PAPER_PATH, force_reindex=True)
        indexed = svc.list_indexed_papers()
        assert isinstance(indexed, list) and PAPER_PATH in indexed

    # -- _is_index_valid branches ---------------------------------------------

    def test_is_index_valid_none_payload(self, svc):
        from models.retrieval import FileSignature
        assert svc._is_index_valid(None, PAPER_PATH, FileSignature(mtime_ns=0, size=0)) is False

    def test_is_index_valid_path_mismatch(self, svc):
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        bad = copy.copy(index)
        object.__setattr__(bad, "paper_path", "wrong/path.pdf")
        assert svc._is_index_valid(bad, PAPER_PATH, index.file_signature) is False

    def test_is_index_valid_mtime_mismatch(self, svc):
        from models.retrieval import FileSignature
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        assert svc._is_index_valid(index, PAPER_PATH, FileSignature(mtime_ns=0, size=index.file_signature.size)) is False

    def test_is_index_valid_size_mismatch(self, svc):
        from models.retrieval import FileSignature
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        assert svc._is_index_valid(index, PAPER_PATH, FileSignature(mtime_ns=index.file_signature.mtime_ns, size=0)) is False

    def test_is_index_valid_chunk_size_mismatch(self, svc, monkeypatch):
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        fs = svc._file_adapter.build_file_signature(svc._file_adapter.papers_dir / PAPER_PATH)
        monkeypatch.setattr(svc.config, "rag_chunk_size", 9999)
        assert svc._is_index_valid(index, PAPER_PATH, fs) is False

    def test_is_index_valid_chunk_overlap_mismatch(self, svc, monkeypatch):
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        fs = svc._file_adapter.build_file_signature(svc._file_adapter.papers_dir / PAPER_PATH)
        monkeypatch.setattr(svc.config, "rag_chunk_overlap", 9999)
        assert svc._is_index_valid(index, PAPER_PATH, fs) is False

    def test_is_index_valid_strategy_version_mismatch(self, svc, monkeypatch):
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        fs = svc._file_adapter.build_file_signature(svc._file_adapter.papers_dir / PAPER_PATH)
        monkeypatch.setattr(svc.config, "rag_strategy_version", "old-version")
        assert svc._is_index_valid(index, PAPER_PATH, fs) is False

    def test_is_index_valid_happy_path(self, svc):
        index = svc._index_repository.load(svc._index_repository.compute_doc_id(PAPER_PATH))
        fs = svc._file_adapter.build_file_signature(svc._file_adapter.papers_dir / PAPER_PATH)
        assert svc._is_index_valid(index, PAPER_PATH, fs) is True
