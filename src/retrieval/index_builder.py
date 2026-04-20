import re
from collections import Counter

from models.retrieval import FileSignature, Index, IndexConfig, IndexedChunk
from retrieval.tokenizer import BM25Tokenizer

# Maps normalized header text to a canonical section name.
_SECTION_ALIASES: dict[str, str] = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "related_work",
    "background": "related_work",
    "preliminaries": "related_work",
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
