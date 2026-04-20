import json
from hashlib import sha256
from pathlib import Path

from models.retrieval import Index


class IndexRepository:
    """Persists and loads RAG index payloads from disk.

    Follows the Repository pattern: abstracts storage details
    from the rest of the application.
    """

    def __init__(self, index_dir: Path):
        self.index_dir = index_dir.resolve()
        self.index_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_doc_id(relative_path: str) -> str:
        return sha256(relative_path.encode("utf-8")).hexdigest()

    def index_file_path(self, doc_id: str) -> Path:
        return self.index_dir / f"{doc_id}.json"

    def load(self, doc_id: str) -> Index | None:
        path = self.index_file_path(doc_id)
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return Index.model_validate(payload)

    def save(self, payload: Index) -> None:
        path = self.index_file_path(payload.doc_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload.model_dump(), handle, indent=2, ensure_ascii=False)

    def list_indexed(self) -> list[str]:
        """Return paper_path for every index file persisted on disk."""
        result = []
        for file in sorted(self.index_dir.glob("*.json")):
            with file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            result.append(data["paper_path"])
        return result
