from typing import Any

from retrieval.file_reader import PaperFileReader
from retrieval.tokenizer import BM25Tokenizer
from retrieval.index_repository import IndexRepository
from retrieval.context_builder import ContextBuilder
from retrieval.index_builder import IndexBuilder
from retrieval.ranker import BM25Ranker
from models.retrieval import FileSignature, Index, IndexConfig, IndexInfo, RetrievalMetadata, RetrievalRequest, RetrievalResponse
from config import PAPERS_DIR, RAG_INDEX_DIR, Config

RAG_QUERY = (
    "methodology study design experiments experimental setup datasets baselines "
    "ablation reproducibility threats validity evaluation metrics"
)


class RetrievalService:

    def __init__(self, config: Config):
        self.config = config
        papers_dir = PAPERS_DIR.resolve()
        index_dir = RAG_INDEX_DIR.resolve()

        tokenizer = BM25Tokenizer()
        
        self._ranker = BM25Ranker(tokenizer)
        self._file_adapter = PaperFileReader(papers_dir)
        self._index_repository = IndexRepository(index_dir)
        self._index_builder = IndexBuilder(tokenizer, config)
        self._context_builder = ContextBuilder(max_context_chars=config.rag_max_context_chars)


    def list_papers(self) -> list[str]:
        """Return relative paths of all available paper files."""
        papers_dir = self._file_adapter.papers_dir
        return sorted(
            f.relative_to(papers_dir).as_posix()
            for f in papers_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in {'.pdf', '.txt'}
        )
        

    def get_indexed_paper(self, paper_path: str) -> IndexInfo:
        """Return index metadata for a specific paper. Raises ValueError if not indexed."""
        _, relative_path = self._file_adapter.resolve_paper_path(paper_path)
        doc_id = self._index_repository.compute_doc_id(relative_path)
        index_payload = self._index_repository.load(doc_id)
        if index_payload is None:
            raise ValueError(f"No index found for paper: {relative_path}")
        return IndexInfo(
            doc_id=index_payload.doc_id,
            paper_path=index_payload.paper_path,
            file_signature=index_payload.file_signature,
            settings=index_payload.settings,
            chunk_count=len(index_payload.chunks),
        )


    def list_indexed_papers(self) -> list[str]:
        """Return paper_path for every paper that has a persisted BM25 index."""
        return self._index_repository.list_indexed()


    def index_paper(self, paper_path: str, force_reindex: bool = False) -> RetrievalMetadata:
        """Build or reuse the BM25 index for a paper. Returns indexing metadata."""
        resolved_path, relative_path = self._file_adapter.resolve_paper_path(paper_path)
        doc_id = self._index_repository.compute_doc_id(relative_path)
        file_signature = self._file_adapter.build_file_signature(resolved_path)

        index_payload = self._index_repository.load(doc_id)
        if force_reindex or not self._is_index_valid(index_payload, relative_path, file_signature):
            index_payload = self._build_index(resolved_path, relative_path, doc_id, file_signature)
            index_status = "rebuilt"
        else:
            index_status = "reused"

        return RetrievalMetadata(
            paper_path=relative_path,
            index_status=index_status,
            chunk_count_total=len(index_payload.chunks),
            chunk_count_retrieved=0,
            top_k=self.config.rag_top_k_default,
        )


    def retrieve_context(self, paper_path: str, top_k: int | None = None, force_reindex: bool = False, query: str | None = None) -> dict[str, Any]:
        """Retrieve context for a given paper path, with optional RAG parameters. Returns context and metadata."""
        request = RetrievalRequest(paper_path=paper_path, top_k=top_k, force_reindex=force_reindex, query=query)
        result = self.retrieve(request)
        return {"context": result.context, "metadata": result.metadata.model_dump(),}


    def prepare_and_get_text(self, paper_path: str, top_k: int | None = None, force_reindex: bool = False) -> tuple[str, str, dict]:
        """Valida il path, costruisce/riusa l'indice e restituisce il testo raw del paper.
        Usato da invoke_from_file per preparare lo stato iniziale del grafo
        prima che i nodi eseguano il RAG per-agente.
        Returns:
            (raw_text, relative_path, retrieval_metadata_dict)
        """
        result = self.retrieve(RetrievalRequest(
            paper_path=paper_path,
            top_k=top_k,
            force_reindex=force_reindex,
            query=RAG_QUERY,
        ))
        relative_path = result.metadata.paper_path
        resolved_path = self._file_adapter.papers_dir / relative_path
        raw_text = self._file_adapter.extract_text(resolved_path)
        return raw_text, relative_path, result.metadata.model_dump()


    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        resolved_path, relative_path = self._file_adapter.resolve_paper_path(request.paper_path)
        doc_id = self._index_repository.compute_doc_id(relative_path)
        top_k_value = request.top_k if request.top_k is not None else self.config.rag_top_k_default
        file_signature = self._file_adapter.build_file_signature(resolved_path)

        index_payload = self._index_repository.load(doc_id)
        if request.force_reindex or not self._is_index_valid(index_payload, relative_path, file_signature):
            index_payload = self._build_index(resolved_path, relative_path, doc_id, file_signature)
            index_status = "rebuilt"
        else:
            index_status = "reused"

        query = request.query or RAG_QUERY
        retrieved_chunks = self._ranker.retrieve(index_payload, query, top_k_value)
        context = self._context_builder.build_context(relative_path, retrieved_chunks)

        metadata = RetrievalMetadata(
            paper_path=relative_path,
            index_status=index_status,
            chunk_count_total=len(index_payload.chunks),
            chunk_count_retrieved=len(retrieved_chunks),
            top_k=top_k_value,
        )

        return RetrievalResponse(
            context=context, 
            metadata=metadata, 
            retrieved_chunks=retrieved_chunks
        )


    def _build_index(self, source_path: str, relative_path: str, doc_id: str, file_signature: FileSignature) -> Index:
        text = self._file_adapter.extract_text(source_path)        
        payload = self._index_builder.build_index(text, relative_path, doc_id, file_signature)
        self._index_repository.save(payload)
        return payload


    def _is_index_valid(self, payload: Index | None, relative_path: str, file_signature: FileSignature) -> bool:
        if payload is None:
            return False
        if payload.paper_path != relative_path:
            return False
        if payload.file_signature.mtime_ns != file_signature.mtime_ns:
            return False
        if payload.file_signature.size != file_signature.size:
            return False
        if payload.settings.chunk_size != self.config.rag_chunk_size:
            return False
        if payload.settings.chunk_overlap != self.config.rag_chunk_overlap:
            return False
        if payload.settings.strategy_version != self.config.rag_strategy_version:
            return False
        return True
