from typing import Any

from adapter.retrieval_file_adapter import RetrievalFileAdapter
from adapter.retrieval_index_adapter import RetrievalIndexAdapter
from adapter.retrieval_tokenizer_adapter import RetrievalTokenizerAdapter
from schemas.retrieval.models import IndexPayload, IndexSettings, RetrievalMetadata, RetrievalRequest, RetrievalResult
from service.retrieval.rag_context_builder import RagContextBuilder
from service.retrieval.rag_index_builder import RagIndexBuilder
from service.retrieval.rag_ranker import RagRanker

from settings import PAPERS_DIR, RAG_INDEX_DIR, Settings

RAG_QUERY = (
    "methodology study design experiments experimental setup datasets baselines "
    "ablation reproducibility threats validity evaluation metrics"
)


class RetrievalService:
    def __init__(self, settings: Settings):
        self.settings = settings
        papers_dir = PAPERS_DIR.resolve()
        index_dir = RAG_INDEX_DIR.resolve()

        tokenizer = RetrievalTokenizerAdapter()
        self.file_adapter = RetrievalFileAdapter(papers_dir)
        self.index_adapter = RetrievalIndexAdapter(index_dir)
        self.index_builder = RagIndexBuilder(tokenizer)
        self.ranker = RagRanker(tokenizer)
        self.context_builder = RagContextBuilder(max_context_chars=settings.rag_max_context_chars)

    def retrieve_for_methodology_review(
        self,
        paper_path: str,
        top_k: int | None = None,
        force_reindex: bool = False,
    ) -> dict[str, Any]:
        request = RetrievalRequest(
            paper_path=paper_path,
            top_k=top_k,
            force_reindex=force_reindex,
            query=RAG_QUERY,
        )
        result = self.retrieve(request)
        return {
            "context": result.context,
            "metadata": result.metadata.model_dump(),
        }

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        resolved_path, relative_path = self.file_adapter.resolve_paper_path(request.paper_path)
        doc_id = self.index_adapter.compute_doc_id(relative_path)
        top_k_value = request.top_k if request.top_k is not None else self.settings.rag_top_k_default
        file_signature = self.file_adapter.build_file_signature(resolved_path)

        index_payload = self.index_adapter.load_index(doc_id)
        if request.force_reindex or not self._is_index_valid(index_payload, relative_path, file_signature):
            index_payload = self._build_index(resolved_path, relative_path, doc_id, file_signature)
            index_status = "rebuilt"
        else:
            index_status = "reused"

        query = request.query or RAG_QUERY
        retrieved_chunks = self.ranker.retrieve(index_payload, query, top_k_value)
        context = self.context_builder.build_context(relative_path, retrieved_chunks)

        metadata = RetrievalMetadata(
            paper_path=relative_path,
            index_status=index_status,
            chunk_count_total=len(index_payload.chunks),
            chunk_count_retrieved=len(retrieved_chunks),
            top_k=top_k_value,
        )

        return RetrievalResult(context=context, metadata=metadata, retrieved_chunks=retrieved_chunks)

    def _build_index(
        self,
        source_path,
        relative_path: str,
        doc_id: str,
        file_signature,
    ) -> IndexPayload:
        text = self.file_adapter.extract_text(source_path)
        payload = self.index_builder.build_index_payload(
            text=text,
            relative_path=relative_path,
            doc_id=doc_id,
            file_signature=file_signature,
            settings=IndexSettings(
                chunk_size=self.settings.rag_chunk_size,
                chunk_overlap=self.settings.rag_chunk_overlap,
                strategy_version=self.settings.rag_strategy_version,
            ),
        )
        self.index_adapter.store_index(payload)
        return payload

    def _is_index_valid(
        self,
        payload: IndexPayload | None,
        relative_path: str,
        file_signature,
    ) -> bool:
        if payload is None:
            return False
        if payload.paper_path != relative_path:
            return False
        if payload.file_signature.mtime_ns != file_signature.mtime_ns:
            return False
        if payload.file_signature.size != file_signature.size:
            return False
        if payload.settings.chunk_size != self.settings.rag_chunk_size:
            return False
        if payload.settings.chunk_overlap != self.settings.rag_chunk_overlap:
            return False
        if payload.settings.strategy_version != self.settings.rag_strategy_version:
            return False

        return True
