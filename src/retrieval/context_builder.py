from models.retrieval import RetrievedChunk


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
