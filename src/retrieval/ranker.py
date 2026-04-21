import math
from collections import Counter

from models.retrieval import Index, IndexedChunk, RetrievedChunk
from retrieval.tokenizer import BM25Tokenizer


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
        return self._bm25_rank(candidates, payload.doc_freq, query_tokens, top_k_value)

    # ------------------------------------------------------------------

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
    ) -> list[RetrievedChunk]:
        query_counts = Counter(query_tokens)
        chunk_count = len(candidates)
        avg_length = sum(c.length for _, c in candidates) / chunk_count
        k1, b = 1.5, 0.75

        scores: list[tuple[float, int, IndexedChunk]] = []
        for original_index, chunk in candidates:
            score = 0.0
            for term, qf in query_counts.items():
                tf = chunk.token_counts.get(term, 0)
                if tf <= 0:
                    continue
                df = int(doc_freq.get(term, 0))
                idf = math.log(1 + ((chunk_count - df + 0.5) / (df + 0.5)))
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
