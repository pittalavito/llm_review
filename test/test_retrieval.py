"""
Unit tests for the RAG pipeline:
  - BM25Tokenizer
  - IndexBuilder (chunking, section detection)
  - BM25Ranker (scoring, section filter, fallback)
  - ContextBuilder (formatting, max_chars limit)
"""
import sys
import pytest

from collections import Counter
from retrieval.indexing import IndexBuilder, _normalize_header, _HEADER_LINE_RE
from retrieval.ranking import BM25Ranker, BM25Tokenizer, ContextBuilder
from models.retrieval import FileSignature, IndexedChunk, Index, IndexConfig, RetrievedChunk

sys.path.insert(0, "src")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tokenizer():
    return BM25Tokenizer()


@pytest.fixture
def dummy_file_signature():
    return FileSignature(mtime_ns=0, size=0)


@pytest.fixture
def dummy_settings():
    class S:
        rag_chunk_size = 200
        rag_chunk_overlap = 50
        rag_strategy_version = "test-v1"
    return S()


@pytest.fixture
def builder(tokenizer, dummy_settings):
    return IndexBuilder(tokenizer, dummy_settings)


@pytest.fixture
def ranker(tokenizer):
    return BM25Ranker(tokenizer)


def make_index(chunks_data: list[tuple[str, str]]) -> Index:
    """Helper: build an Index from (section, text) pairs."""
    tokenizer = BM25Tokenizer()
    doc_freq: Counter = Counter()
    indexed_chunks = []
    for section, text in chunks_data:
        tokens = tokenizer.tokenize(text)
        counts = Counter(tokens)
        doc_freq.update(set(counts.keys()))
        indexed_chunks.append(IndexedChunk(
            text=text,
            token_counts=dict(counts),
            length=sum(counts.values()),
            section=section,
        ))
    return Index(
        doc_id="test-doc",
        paper_path="test/paper.pdf",
        file_signature=FileSignature(mtime_ns=0, size=0),
        settings=IndexConfig(chunk_size=200, chunk_overlap=50, strategy_version="test"),
        doc_freq=dict(doc_freq),
        chunks=indexed_chunks,
    )


# ---------------------------------------------------------------------------
# BM25Tokenizer
# ---------------------------------------------------------------------------

class TestBM25Tokenizer:

    def test_lowercase(self, tokenizer):
        assert tokenizer.tokenize("Hello World") == ["hello", "world"]

    def test_strips_punctuation(self, tokenizer):
        assert tokenizer.tokenize("hello, world!") == ["hello", "world"]

    def test_alphanumeric_kept(self, tokenizer):
        assert "bm25" in tokenizer.tokenize("BM25 algorithm")

    def test_empty_string(self, tokenizer):
        assert tokenizer.tokenize("") == []

    def test_numbers(self, tokenizer):
        assert tokenizer.tokenize("page 42") == ["page", "42"]


# ---------------------------------------------------------------------------
# IndexBuilder — section detection
# ---------------------------------------------------------------------------

class TestSectionDetection:

    def test_normalize_header_pypdf_artifact(self):
        assert _normalize_header("I NTRODUCTION") == "introduction"
        assert _normalize_header("E XPERIMENTAL RESULTS") == "experimental results"
        assert _normalize_header("C ONCLUSION") == "conclusion"

    def test_normalize_header_clean(self):
        assert _normalize_header("ABSTRACT") == "abstract"
        assert _normalize_header("REFERENCES") == "references"

    def test_header_regex_matches_numbered(self):
        assert _HEADER_LINE_RE.match("1 I NTRODUCTION") is not None
        assert _HEADER_LINE_RE.match("2 M ETHODS") is not None

    def test_header_regex_rejects_long_lines(self):
        long = "A" * 90
        assert _HEADER_LINE_RE.match(long) is None

    def test_header_regex_rejects_lowercase(self):
        assert _HEADER_LINE_RE.match("introduction") is None


class TestIndexBuilderChunking:

    def test_single_section_detected(self, builder, dummy_file_signature):
        text = "ABSTRACT\nThis paper proposes a novel method for molecule captioning."
        index = builder.build_index(text, "paper.pdf", "doc1", dummy_file_signature)
        sections = {c.section for c in index.chunks}
        assert "abstract" in sections

    def test_fallback_to_body_when_no_headers(self, builder, dummy_file_signature):
        text = "This is a plain text with no section headers at all."
        index = builder.build_index(text, "paper.pdf", "doc1", dummy_file_signature)
        sections = {c.section for c in index.chunks}
        assert sections == {"body"}

    def test_multiple_sections(self, builder, dummy_file_signature):
        text = (
            "ABSTRACT\nThis paper presents a new approach.\n\n"
            "INTRODUCTION\nThe problem of molecule captioning is challenging.\n\n"
            "REFERENCES\nSmith et al., 2020."
        )
        index = builder.build_index(text, "paper.pdf", "doc1", dummy_file_signature)
        sections = {c.section for c in index.chunks}
        assert "abstract" in sections
        assert "introduction" in sections
        assert "other" in sections  # references → other

    def test_chunk_count_increases_with_smaller_size(self, tokenizer, dummy_file_signature):
        text = "word " * 500

        class BigChunk:
            rag_chunk_size = 400
            rag_chunk_overlap = 50
            rag_strategy_version = "test"

        class SmallChunk:
            rag_chunk_size = 100
            rag_chunk_overlap = 20
            rag_strategy_version = "test"

        big = IndexBuilder(tokenizer, BigChunk()).build_index(text, "p.pdf", "d1", dummy_file_signature)
        small = IndexBuilder(tokenizer, SmallChunk()).build_index(text, "p.pdf", "d2", dummy_file_signature)
        assert len(small.chunks) > len(big.chunks)

    def test_raises_on_empty_text(self, builder, dummy_file_signature):
        with pytest.raises(ValueError, match="empty"):
            builder.build_index("", "paper.pdf", "doc1", dummy_file_signature)

    def test_invalid_chunk_size_raises(self, builder, dummy_file_signature):
        with pytest.raises(ValueError):
            builder._sliding_window("text", chunk_size=0, chunk_overlap=0)

    def test_invalid_overlap_raises(self, builder, dummy_file_signature):
        with pytest.raises(ValueError):
            builder._sliding_window("text", chunk_size=100, chunk_overlap=100)


# ---------------------------------------------------------------------------
# BM25Ranker
# ---------------------------------------------------------------------------

class TestBM25Ranker:

    def test_relevant_chunk_ranked_first(self, ranker):
        index = make_index([
            ("methods", "The experimental design uses ablation study and baselines."),
            ("introduction", "This paper introduces a novel molecule captioning approach."),
            ("results", "Results show improvements on standard benchmarks."),
        ])
        results = ranker.retrieve(index, "ablation study experimental", top_k=3)
        assert results[0].section == "methods"

    def test_top_k_limits_results(self, ranker):
        index = make_index([(f"body", f"word{i} " * 20) for i in range(10)])
        results = ranker.retrieve(index, "word1", top_k=3)
        assert len(results) <= 3

    def test_section_filter_returns_only_matching(self, ranker):
        index = make_index([
            ("methods", "experimental design methodology ablation reproducibility"),
            ("methods", "statistical analysis validity datasets baselines"),
            ("introduction", "novel approach motivation problem statement"),
            ("results", "accuracy precision recall f1 score"),
        ])
        results = ranker.retrieve(index, "experimental methodology", top_k=5, sections=["methods"])
        assert all(r.section == "methods" for r in results)

    def test_section_filter_fallback_when_too_few(self, ranker):
        index = make_index([
            ("methods", "experimental design evaluation"),
            ("introduction", "novel experimental approach motivation problem statement research"),
            ("results", "experimental accuracy improvements benchmark evaluation metrics"),
            ("conclusion", "we conclude experimental future work directions evaluation"),
        ])
        # Only 1 methods chunk, top_k=3 → should fallback to all sections
        # Query matches all chunks so BM25 returns results from multiple sections
        results = ranker.retrieve(index, "experimental evaluation", top_k=3, sections=["methods"])
        sections_found = {r.section for r in results}
        assert len(sections_found) > 1

    def test_empty_query_returns_empty(self, ranker):
        index = make_index([("body", "some text here")])
        results = ranker.retrieve(index, "", top_k=5)
        assert results == []

    def test_rank_starts_at_one(self, ranker):
        index = make_index([
            ("body", "machine learning deep neural network classification"),
            ("body", "machine learning natural language processing text classification"),
        ])
        results = ranker.retrieve(index, "machine learning classification", top_k=2)
        assert results[0].rank == 1
        assert results[1].rank == 2

    def test_scores_are_positive(self, ranker):
        index = make_index([("body", "experimental results show improvements")])
        results = ranker.retrieve(index, "experimental results", top_k=5)
        assert all(r.score > 0 for r in results)

    def test_section_propagated_to_result(self, ranker):
        index = make_index([("methods", "methodology experimental design ablation")])
        results = ranker.retrieve(index, "methodology", top_k=1)
        assert results[0].section == "methods"


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------

class TestContextBuilder:

    def make_chunks(self, texts: list[str]) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(rank=i + 1, score=1.0, index=i, text=t, section="body")
            for i, t in enumerate(texts)
        ]

    def test_empty_chunks_returns_no_results_message(self):
        cb = ContextBuilder(max_context_chars=1000)
        result = cb.build_context("paper.pdf", [])
        assert "No relevant chunks" in result

    def test_includes_paper_source(self):
        cb = ContextBuilder(max_context_chars=1000)
        chunks = self.make_chunks(["some text"])
        result = cb.build_context("my/paper.pdf", chunks)
        assert "my/paper.pdf" in result

    def test_respects_max_context_chars(self):
        cb = ContextBuilder(max_context_chars=100)
        chunks = self.make_chunks(["word " * 50, "word " * 50, "word " * 50])
        result = cb.build_context("paper.pdf", chunks)
        assert len(result) <= 100 + 50  # small tolerance for header

    def test_chunk_rank_in_output(self):
        cb = ContextBuilder(max_context_chars=5000)
        chunks = self.make_chunks(["first chunk text"])
        result = cb.build_context("paper.pdf", chunks)
        assert "Chunk #1" in result
