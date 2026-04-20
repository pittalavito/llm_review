import math
from collections import Counter

from models.retrieval import Index, RetrievedChunk
from retrieval.tokenizer import BM25Tokenizer


class BM25Ranker:
    def __init__(self, tokenizer: BM25Tokenizer):
        self.tokenizer = tokenizer

    def retrieve(self, payload: Index, query: str, top_k: int) -> list[RetrievedChunk]:
        top_k_value = max(1, min(top_k, 20))
        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        query_counts = Counter(query_tokens)
        chunk_count = len(payload.chunks)
        avg_length = sum(chunk.length for chunk in payload.chunks) / chunk_count
        doc_freq = payload.doc_freq

        scores: list[tuple[float, int, object]] = []
        k1 = 1.5
        b = 0.75

        for index, chunk in enumerate(payload.chunks):
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
                scores.append((score, index, chunk))

        scores.sort(key=lambda item: item[0], reverse=True)
        selected = scores[:top_k_value]

        return [
            RetrievedChunk(
                rank=rank + 1,
                score=round(score, 4),
                index=chunk_index,
                text=chunk.text,
            )
            for rank, (score, chunk_index, chunk) in enumerate(selected)
        ]
