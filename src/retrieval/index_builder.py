from collections import Counter

from models.retrieval import FileSignature, Index, IndexConfig, IndexedChunk
from retrieval.tokenizer import BM25Tokenizer


class IndexBuilder:
    
    def __init__(self, tokenizer: BM25Tokenizer, settings):
        self.tokenizer = tokenizer
        self.settings = settings


    def build_index(self, text: str, relative_path: str, doc_id: str, file_signature: FileSignature) -> Index:
        index_setting = self._build_index_config()
        chunks = self._chunk_text(text, chunk_size=index_setting.chunk_size, chunk_overlap=index_setting.chunk_overlap)
        
        if not chunks:
            raise ValueError("The extracted document text is empty after chunking.")

        indexed_chunks: list[IndexedChunk] = []
        document_frequency: Counter[str] = Counter()

        for chunk_text in chunks:
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

 
    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
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