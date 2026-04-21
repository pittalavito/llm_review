import logging

from retrieval.file_reader import PaperFileReader
from retrieval.tokenizer import BM25Tokenizer
from retrieval.index_repository import IndexRepository
from retrieval.context_builder import ContextBuilder
from retrieval.index_builder import IndexBuilder
from retrieval.ranker import BM25Ranker
from models.retrieval import FileSignature, Index, IndexInfo, RetrievalMetadata
from config import PAPERS_DIR, RAG_INDEX_DIR, Config


logger = logging.getLogger(__name__)

_LOGGER_PREFIX = "[RetrievalService]"


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
        logger.info(f"{_LOGGER_PREFIX} Listing papers in directory: {PAPERS_DIR}")
        papers_dir = self._file_adapter.papers_dir
        return sorted(
            f.relative_to(papers_dir).as_posix()
            for f in papers_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in {'.pdf', '.txt'}
        )
        

    def get_indexed_paper(self, paper_path: str) -> IndexInfo:
        """Return index metadata for a specific paper. Raises ValueError if not indexed."""
        logger.info(f"{_LOGGER_PREFIX} Getting index metadata for paper: {paper_path}")
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
        logger.info(f"{_LOGGER_PREFIX} Listing indexed papers")
        return self._index_repository.list_indexed()


    def index_paper(self, paper_path: str, force_reindex: bool = False) -> RetrievalMetadata:
        """Build or reuse the BM25 index for a paper. Returns indexing metadata."""
        logger.info(f"{_LOGGER_PREFIX} Indexing paper: {paper_path} with force_reindex={force_reindex}")
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


    def retrieve_for_agent(self, paper_path: str, query: str, sections: list[str] | None = None, top_k: int | None = None) -> str:
        """Retrieve context string for a specific agent (section-aware).
        Used by RetrievalContextProvider — returns only the context string.
        """
        logger.info(f"{_LOGGER_PREFIX} Retrieving context for paper: {paper_path} for sections: {sections}, top_k: {top_k}")
        resolved_path, relative_path = self._file_adapter.resolve_paper_path(paper_path)
        doc_id = self._index_repository.compute_doc_id(relative_path)
        top_k_value = top_k or self.config.rag_top_k_default
        file_signature = self._file_adapter.build_file_signature(resolved_path)

        index_payload = self._index_repository.load(doc_id)
        if not self._is_index_valid(index_payload, relative_path, file_signature):
            index_payload = self._build_index(resolved_path, relative_path, doc_id, file_signature)

        retrieved_chunks = self._ranker.retrieve(index_payload, query, top_k_value, sections=sections)
        return self._context_builder.build_context(relative_path, retrieved_chunks)


    def _build_index(self, source_path: str, relative_path: str, doc_id: str, file_signature: FileSignature) -> Index:
        logger.info(f"{_LOGGER_PREFIX} Building index for paper: {relative_path}")
        text = self._file_adapter.extract_text(source_path)        
        payload = self._index_builder.build_index(text, relative_path, doc_id, file_signature)
        self._index_repository.save(payload)
        return payload


    def _is_index_valid(self, payload: Index | None, relative_path: str, file_signature: FileSignature) -> bool:
        if payload is None:
            logger.info(f"{_LOGGER_PREFIX} No existing index payload found for paper: {relative_path}")
            return False
        if payload.paper_path != relative_path:
            logger.info(f"{_LOGGER_PREFIX} Paper path mismatch for paper: {relative_path}. Expected: {relative_path}, Found: {payload.paper_path}")
            return False
        if payload.file_signature.mtime_ns != file_signature.mtime_ns:
            logger.info(f"{_LOGGER_PREFIX} File modification time mismatch for paper: {relative_path}. Expected: {file_signature.mtime_ns}, Found: {payload.file_signature.mtime_ns}")
            return False
        if payload.file_signature.size != file_signature.size:
            logger.info(f"{_LOGGER_PREFIX} File size mismatch for paper: {relative_path}. Expected: {file_signature.size}, Found: {payload.file_signature.size}")
            return False
        if payload.settings.chunk_size != self.config.rag_chunk_size:
            logger.info(f"{_LOGGER_PREFIX} Chunk size mismatch for paper: {relative_path}. Expected: {self.config.rag_chunk_size}, Found: {payload.settings.chunk_size}")
            return False
        if payload.settings.chunk_overlap != self.config.rag_chunk_overlap:
            logger.info(f"{_LOGGER_PREFIX} Chunk overlap mismatch for paper: {relative_path}. Expected: {self.config.rag_chunk_overlap}, Found: {payload.settings.chunk_overlap}")
            return False
        if payload.settings.strategy_version != self.config.rag_strategy_version:
            logger.info(f"{_LOGGER_PREFIX} Strategy version mismatch for paper: {relative_path}. Expected: {self.config.rag_strategy_version}, Found: {payload.settings.strategy_version}")
            return False
        return True
