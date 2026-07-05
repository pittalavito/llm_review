import math
import re
from collections import Counter

from models.retrieval import Index, IndexedChunk, RetrievedChunk

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


class BM25Tokenizer:
    @staticmethod
    def tokenize(text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class BM25Ranker:
    def __init__(self, tokenizer: BM25Tokenizer):
        self.tokenizer = tokenizer

    def retrieve(
        self,
        payload: Index,
        query: str,
        top_k: int,
        sections: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        top_k_value = max(1, min(top_k, 20))
        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        candidates = self._select_candidates(payload.chunks, sections, top_k_value)
        return self._bm25_rank(candidates, payload.doc_freq, query_tokens, top_k_value, len(payload.chunks))

    def _select_candidates(
        self,
        chunks: list[IndexedChunk],
        sections: list[str] | None,
        top_k: int,
    ) -> list[tuple[int, IndexedChunk]]:
        """Return (original_index, chunk) pairs filtered by section.
        Falls back to all chunks if section filter yields fewer than top_k results.
        """
        if not sections:
            return list(enumerate(chunks))

        filtered = [(i, c) for i, c in enumerate(chunks) if c.section in sections]

        # Fallback: not enough section-specific chunks → use all
        if len(filtered) < top_k:
            return list(enumerate(chunks))

        return filtered

    def _bm25_rank(
        self,
        candidates: list[tuple[int, IndexedChunk]],
        doc_freq: dict[str, int],
        query_tokens: list[str],
        top_k: int,
        total_chunks: int | None = None,
    ) -> list[RetrievedChunk]:
        query_counts = Counter(query_tokens)
        # IDF must use the total corpus size (all chunks), not just the filtered candidates,
        # otherwise doc_freq > candidate_count produces negative IDF → zero results.
        n = total_chunks if total_chunks is not None else len(candidates)
        avg_length = sum(c.length for _, c in candidates) / len(candidates)
        k1, b = 1.5, 0.75

        scores: list[tuple[float, int, IndexedChunk]] = []
        for original_index, chunk in candidates:
            score = 0.0
            for term, qf in query_counts.items():
                tf = chunk.token_counts.get(term, 0)
                if tf <= 0:
                    continue
                df = int(doc_freq.get(term, 0))
                idf = math.log(1 + ((n - df + 0.5) / (df + 0.5)))
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (chunk.length / avg_length))
                score += qf * idf * (numerator / denominator)
            if score > 0:
                scores.append((score, original_index, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievedChunk(
                rank=rank + 1,
                score=round(score, 4),
                index=original_index,
                text=chunk.text,
                section=chunk.section,
            )
            for rank, (score, original_index, chunk) in enumerate(scores[:top_k])
        ]


class ContextBuilder:
    def __init__(self, max_context_chars: int):
        self.max_context_chars = max_context_chars

    def build_context(self, relative_path: str, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return f"Paper source: {relative_path}\nNo relevant chunks were retrieved."

        parts = [
            f"Paper source: {relative_path}",
            "Retrieved chunks:",
        ]

        total_chars = 0
        for chunk in chunks:
            block = f"\n[Chunk #{chunk.rank} | score={chunk.score}]\n{chunk.text}"
            if total_chars + len(block) > self.max_context_chars:
                break
            parts.append(block)
            total_chars += len(block)

        return "\n".join(parts).strip()
