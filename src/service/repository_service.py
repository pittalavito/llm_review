from sqlalchemy.engine import Engine

from pathlib import Path

from domain.db.result_repository import ResultRepository
from domain.db.prompt_repository import PromptRepository
from domain.db.paper_repository import PaperRepository
from domain.db.tables import PromptVersionTable

from models.agent import AgentName
from models.paper import Paper
from models.run_record import AgentRun, RunRecord, RunSummary


class RepositoryService:
    """Service-layer facade over the two DB repositories.
    The container and all services above interact exclusively with this class;
    the concrete SQL implementations stay hidden inside domain/db/.
    """

    def __init__(self, engine: Engine):
        self._result_repository = ResultRepository(engine)
        self._prompt_repository = PromptRepository(engine)
        self._paper_repository = PaperRepository(engine)

    # ------------------------------------------------------------------
    # Run results
    # ------------------------------------------------------------------

    @staticmethod
    def build_run_id(paper_path: str) -> str:
        return ResultRepository.build_run_id(paper_path)

    def save(self, record: RunRecord) -> str:
        return self._result_repository.save(record)

    def list_runs(self) -> list[RunSummary]:
        return self._result_repository.list()

    def get_run(self, run_id: str) -> RunRecord:
        return self._result_repository.get(run_id)

    def get_agent_runs(
        self,
        run_id: str,
        agent_name: AgentName | None = None,
        round_index: int | None = None,
    ) -> list[AgentRun]:
        return self._result_repository.get_agent_runs(run_id, agent_name=agent_name, round_index=round_index)

    # ------------------------------------------------------------------
    # Prompt versions
    # ------------------------------------------------------------------

    def list_prompts(self, agent_role: str | None = None, include_inactive: bool = False) -> list[PromptVersionTable]:
        return self._prompt_repository.list(agent_role, include_inactive)

    def get_prompt(self, version_id: int) -> PromptVersionTable:
        return self._prompt_repository.get(version_id)

    def get_by_role_label(self, agent_role: str, version_label: str, only_active: bool = True) -> PromptVersionTable:
        """Duck-type compatible with PromptRepository — used by agent_service._resolve_prompt_template."""
        
        return self._prompt_repository.get_by_role_label(agent_role, version_label, only_active)

    def create_prompt(self, agent_role: str, version_label: str, template: str, description: str | None = None) -> PromptVersionTable:
        return self._prompt_repository.create(agent_role, version_label, template, description)

    def update_prompt_meta(self, version_id: int, description: str | None = None, is_active: bool | None = None) -> PromptVersionTable:
        return self._prompt_repository.update_meta(version_id, description, is_active)

    def seed_defaults(self, seeds: list[tuple[str, str, str, str]]) -> int:
        return self._prompt_repository.seed_defaults(seeds)

    # ------------------------------------------------------------------
    # Papers
    # ------------------------------------------------------------------

    def list_papers_catalog(self) -> list[Paper]:
        return self._paper_repository.list()

    def list_paper_paths(self) -> list[str]:
        return self._paper_repository.list_paths()

    def list_openreview_papers(self) -> list[Paper]:
        return self._paper_repository.list_openreview()

    def get_paper(self, paper_path: str) -> Paper:
        return self._paper_repository.get_by_path(paper_path)

    def seed_papers(self, papers_dir: Path, index_path: Path) -> int:
        return self._paper_repository.seed_from_sources(papers_dir, index_path)
