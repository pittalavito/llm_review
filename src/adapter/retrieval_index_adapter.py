import json
from hashlib import sha256
from pathlib import Path

from schemas.retrieval.models import IndexPayload


class RetrievalIndexAdapter:
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir.resolve()
        self.index_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_doc_id(relative_path: str) -> str:
        return sha256(relative_path.encode("utf-8")).hexdigest()

    def index_file_path(self, doc_id: str) -> Path:
        return self.index_dir / f"{doc_id}.json"

    def load_index(self, doc_id: str) -> IndexPayload | None:
        path = self.index_file_path(doc_id)
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return IndexPayload.model_validate(payload)

    def store_index(self, payload: IndexPayload) -> None:
        path = self.index_file_path(payload.doc_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload.model_dump(), handle, indent=2, ensure_ascii=False)
