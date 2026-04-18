import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from schemas.retrieval.models import RetrievalRequest
from service.retrieval_service import RetrievalService
from settings import PAPERS_DIR, Settings


def test_retrieve_supports_query_override_and_strategy_version_rebuild():
    service = RetrievalService(Settings())

    paper_dir = PAPERS_DIR / f"test-{uuid4().hex}"
    paper_dir.mkdir(parents=True, exist_ok=True)
    paper_file = paper_dir / "paper.txt"
    paper_file.write_text(
        "This text discusses methodology, reproducibility, and ablation setup.",
        encoding="utf-8",
    )

    relative_path = f"{paper_dir.name}/paper.txt"

    try:
        first = service.retrieve(
            RetrievalRequest(
                paper_path=relative_path,
                top_k=3,
                force_reindex=False,
                query="reproducibility ablation",
            )
        )
        assert first.metadata.index_status == "rebuilt"
        assert first.metadata.top_k == 3

        second = service.retrieve(
            RetrievalRequest(
                paper_path=relative_path,
                top_k=3,
                force_reindex=False,
                query="reproducibility ablation",
            )
        )
        assert second.metadata.index_status == "reused"

        service.settings.rag_strategy_version = "bm25-v2"
        third = service.retrieve(
            RetrievalRequest(
                paper_path=relative_path,
                top_k=3,
                force_reindex=False,
                query="reproducibility ablation",
            )
        )
        assert third.metadata.index_status == "rebuilt"
    finally:
        if paper_file.exists():
            paper_file.unlink()
        if paper_dir.exists():
            paper_dir.rmdir()
