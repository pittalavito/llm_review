from pathlib import Path

from pypdf import PdfReader

from schemas.retrieval.models import FileSignature

ALLOWED_EXTENSIONS = {".txt", ".pdf"}


class RetrievalFileAdapter:
    def __init__(self, papers_dir: Path):
        self.papers_dir = papers_dir.resolve()

    def resolve_paper_path(self, paper_path: str) -> tuple[Path, str]:
        normalized = paper_path.replace("\\", "/").strip("/")
        candidate = (self.papers_dir / normalized).resolve()

        if self.papers_dir not in candidate.parents and candidate != self.papers_dir:
            raise ValueError("Invalid paper path: path traversal is not allowed.")
        if not candidate.exists() or not candidate.is_file():
            raise ValueError(f"Paper file not found: {normalized}")
        if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("Unsupported file type. Use .txt or .pdf files.")

        relative_path = candidate.relative_to(self.papers_dir).as_posix()
        return candidate, relative_path

    def extract_text(self, source_path: Path) -> str:
        if source_path.suffix.lower() == ".txt":
            text = source_path.read_text(encoding="utf-8")
        else:
            reader = PdfReader(str(source_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)

        normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if not normalized:
            raise ValueError("Could not extract text from the selected paper file.")
        return normalized

    @staticmethod
    def build_file_signature(source_path: Path) -> FileSignature:
        source_stat = source_path.stat()
        return FileSignature(mtime_ns=source_stat.st_mtime_ns, size=source_stat.st_size)
