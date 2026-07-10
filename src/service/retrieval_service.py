import logging

from domain.retrieval.cache import build_index_repository
from domain.retrieval.indexing import IndexBuilder, PaperFileReader
from domain.retrieval.ranking import BM25Ranker, BM25Tokenizer, ContextBuilder
from models.retrieval import FileSignature, Index, IndexInfo, RetrievalMetadata
from config import PAPERS_DIR, RAG_INDEX_DIR, Config


logger = logging.getLogger(__name__)

_LOGGER_PREFIX = "[RetrievalService]"

class RetrievalService:

    def __init__(self, config: Config):
        
        
        papers_dir = PAPERS_DIR.resolve()
        index_dir = RAG_INDEX_DIR.resolve()
        tokenizer = BM25Tokenizer()
        
        self.config = config
        self._ranker = BM25Ranker(tokenizer)
        self._file_adapter = PaperFileReader(papers_dir)
        self._index_repository = build_index_repository(config, index_dir)
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

    def extract_abstract(self, paper_path: str) -> str:
        """Return the abstract text from the paper's BM25 index.
        Used as a dynamic BM25 query so retrieval is grounded in the paper's own
        vocabulary rather than a generic keyword list.  Falls back to the first
        non-preamble chunk when no abstract section is found (e.g. arXiv papers
        whose abstract is not labelled explicitly).
        """
        
        _, relative_path = self._file_adapter.resolve_paper_path(paper_path)
        doc_id = self._index_repository.compute_doc_id(relative_path)
        index_payload = self._index_repository.load(doc_id)

        if index_payload is None:
            return ""

        abstract_chunks = [c for c in index_payload.chunks if c.section == "abstract"]
        if abstract_chunks:
            return " ".join(c.text for c in abstract_chunks)

        # Fallback: use the introduction if the abstract wasn't labelled
        intro_chunks = [c for c in index_payload.chunks if c.section == "introduction"]
        if intro_chunks:
            return intro_chunks[0].text

        return index_payload.chunks[0].text if index_payload.chunks else ""

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
        logger.info(f"{_LOGGER_PREFIX} Retrieved {len(retrieved_chunks)} chunks for paper: {relative_path}")
        return self._context_builder.build_context(relative_path, retrieved_chunks)

    def _build_index(self, source_path: str, relative_path: str, doc_id: str, file_signature: FileSignature) -> Index:
        logger.info(f"{_LOGGER_PREFIX} Building index for paper: {relative_path}")
        
        text = self._file_adapter.extract_text(source_path)        
        payload = self._index_builder.build_index(text, relative_path, doc_id, file_signature)
        self._index_repository.save(payload)
        return payload

    def _is_index_valid(self, payload: Index | None, relative_path: str, file_signature: FileSignature) -> bool:
        if payload is None:
            return False

        checks = [
            (payload.paper_path != relative_path, "paper path changed"),
            (payload.file_signature.mtime_ns != file_signature.mtime_ns, "file modified (mtime)"),
            (payload.file_signature.size != file_signature.size, "file size changed"),
            (payload.settings.chunk_size != self.config.rag_chunk_size, "chunk_size changed"),
            (payload.settings.chunk_overlap != self.config.rag_chunk_overlap, "chunk_overlap changed"),
            (payload.settings.strategy_version != self.config.rag_strategy_version, "strategy_version changed"),
        ]

        for is_stale, reason in checks:
            if is_stale:
                logger.info(f"{_LOGGER_PREFIX} Index stale for '{relative_path}': {reason}")
                return False

        return True
