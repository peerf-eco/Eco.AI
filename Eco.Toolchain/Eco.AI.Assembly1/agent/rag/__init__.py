"""RAG over EcoOS marketplace_cache.

Independent of langchain (V7 stack uses pi_ai). Public surface:
    - chunker_base.Chunker / Chunk
    - chunker_naive.NaiveChunker / NaiveOverlapChunker
    - chunker_recursive.RecursiveChunker
    - chunker_ast.ASTChunker  (with regex fallback)
    - embedder.Embedder
    - store.RagStore
    - retrieve.HybridRetriever
    - ingest.ingest_cache
"""
from agent.rag.chunker_base import Chunker, Chunk, ChunkKind

__all__ = ["Chunker", "Chunk", "ChunkKind"]
