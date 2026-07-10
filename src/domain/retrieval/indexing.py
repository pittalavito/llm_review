import json
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path

from pypdf import PdfReader

from models.retrieval import FileSignature, Index, IndexConfig, IndexedChunk
from domain.retrieval.ranking import BM25Tokenizer

ALLOWED_EXTENSIONS = {".txt", ".pdf"}

# Maps normalized header text to a canonical section name.
_SECTION_ALIASES: dict[str, str] = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "methods",
    "preliminaries": "methods",
    "method": "methods",
    "methods": "methods",
    "methodology": "methods",
    "approach": "methods",
    "model": "methods",
    "framework": "methods",
    "experiment": "experiments",
    "experiments": "experiments",
    "experimental setup": "experiments",
    "experimental results": "results",
    "evaluation": "experiments",
    "result": "results",
    "results": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "future work": "conclusion",
    "molecule captioning": "methods",
    "molecule captioning and probing rules": "methods",
    "acknowledgment": "other",
    "acknowledgments": "other",
    "reference": "other",
    "references": "other",
    "urm statement": "other",
}

# Detects short all-caps lines that are likely section headers (pypdf artifact aware).
# pypdf sometimes inserts a space after the first letter: "I NTRODUCTION", "E XPERIMENTS"
_HEADER_LINE_RE = re.compile(
    r"^(?:(\d+|[A-Z])\s+)?([A-Z][A-Z\s]{2,60})$"
)

# pypdf artifact: single uppercase letter followed by a space before the rest of the word.
# e.g. "I NTRODUCTION" -> "INTRODUCTION", "E XPERIMENTAL RESULTS" -> "EXPERIMENTAL RESULTS"
_PYPDF_SPLIT_RE = re.compile(r"\b([A-Z])\s([A-Z]{2,})\b")


def _normalize_header(raw: str) -> str:
    """Fix pypdf spacing artifacts and return a clean lowercase header string."""
    fixed = _PYPDF_SPLIT_RE.sub(lambda m: m.group(1) + m.group(2), raw)
    return fixed.strip().lower()


class IndexBuilder:

    def __init__(self, tokenizer: BM25Tokenizer, settings):
        self.tokenizer = tokenizer
        self.settings = settings

    def build_index(self, text: str, relative_path: str, doc_id: str, file_signature: FileSignature) -> Index:
        index_setting = self._build_index_config()
        section_chunks = self._chunk_by_section(
            text,
            chunk_size=index_setting.chunk_size,
            chunk_overlap=index_setting.chunk_overlap,
        )

        if not section_chunks:
            raise ValueError("The extracted document text is empty after chunking.")

        indexed_chunks: list[IndexedChunk] = []
        document_frequency: Counter[str] = Counter()

        for section, chunk_text in section_chunks:
            tokens = self.tokenizer.tokenize(chunk_text)
            token_counts = Counter(tokens)

            if not token_counts:
                continue

            document_frequency.update(set(token_counts.keys()))
            indexed_chunks.append(
                IndexedChunk(
                    text=chunk_text,
                    token_counts=dict(token_counts),
                    length=sum(token_counts.values()),
                    section=section,
                )
            )

        if not indexed_chunks:
            raise ValueError("Unable to build retrieval chunks from the given file.")

        return Index(
            doc_id=doc_id,
            paper_path=relative_path,
            file_signature=file_signature,
            settings=index_setting,
            doc_freq=dict(document_frequency),
            chunks=indexed_chunks,
        )

    def _chunk_by_section(self, text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[str, str]]:
        if chunk_size <= 0:
            raise ValueError("Invalid chunk size. It must be greater than zero.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("Invalid chunk overlap. It must be between 0 and chunk_size - 1.")

        sections = self._split_into_sections(text)
        result: list[tuple[str, str]] = []
        for section_name, section_text in sections:
            for chunk in self._sliding_window(section_text, chunk_size, chunk_overlap):
                result.append((section_name, chunk))
        return result

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """
        Detect section headers line by line, handling pypdf spacing artifacts.
        Returns a list of (canonical_section, section_text) pairs.
        """
        lines = text.splitlines()
        boundaries: list[tuple[int, str]] = []  # (char_offset, canonical_section)

        char_offset = 0
        for line in lines:
            stripped = line.strip()
            canonical = self._match_header(stripped)
            if canonical:
                boundaries.append((char_offset, canonical))
            char_offset += len(line) + 1  # +1 for the newline

        if not boundaries:
            return [("body", text)]

        sections: list[tuple[str, str]] = []

        preamble = text[: boundaries[0][0]].strip()
        if preamble:
            sections.append(("preamble", preamble))

        for i, (start, section_name) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            body = text[start:end].strip()
            if body:
                sections.append((section_name, body))

        return sections

    def _match_header(self, line: str) -> str | None:
        """Return canonical section name if the line is a section header, else None."""
        if not line or len(line) > 80:
            return None

        m = _HEADER_LINE_RE.match(line)
        if not m:
            return None

        # Normalize the header text (fixes pypdf artifacts, lowercases)
        raw_header = m.group(2) if m.group(2) else line
        normalized = _normalize_header(raw_header)

        # Exact match
        if normalized in _SECTION_ALIASES:
            return _SECTION_ALIASES[normalized]

        # Partial match: check if normalized starts with a known key
        for key, canonical in _SECTION_ALIASES.items():
            if normalized.startswith(key):
                return canonical

        return None

    def _sliding_window(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        if chunk_size <= 0:
            raise ValueError("Invalid chunk size. It must be greater than zero.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("Invalid chunk overlap. It must be between 0 and chunk_size - 1.")
        chunks: list[str] = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == text_length:
                break
            start = end - chunk_overlap
        return chunks

    def _build_index_config(self) -> IndexConfig:
        return IndexConfig(
            chunk_size=self.settings.rag_chunk_size,
            chunk_overlap=self.settings.rag_chunk_overlap,
            strategy_version=self.settings.rag_strategy_version,
        )


class PaperFileReader:

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
