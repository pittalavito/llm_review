import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from adapter.retrieval_file_adapter import RetrievalFileAdapter
from settings import PAPERS_DIR


def test_resolve_paper_path_rejects_path_traversal():
    adapter = RetrievalFileAdapter(PAPERS_DIR)

    with pytest.raises(ValueError):
        adapter.resolve_paper_path("../secret.txt")


def test_resolve_paper_path_rejects_unsupported_extension():
    adapter = RetrievalFileAdapter(PAPERS_DIR)
    test_dir = PAPERS_DIR / f"test-{uuid4().hex}"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "paper.zip"
    test_file.write_text("dummy", encoding="utf-8")

    try:
        with pytest.raises(ValueError):
            adapter.resolve_paper_path(f"{test_dir.name}/paper.zip")
    finally:
        if test_file.exists():
            test_file.unlink()
        if test_dir.exists():
            test_dir.rmdir()
