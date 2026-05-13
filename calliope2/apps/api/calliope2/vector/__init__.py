"""pgvector helpers: embedding generation + cosine-distance search."""

from calliope2.vector.embedding import embed_text, try_embed_text
from calliope2.vector.search import SearchHit, search_frames

__all__ = ["SearchHit", "embed_text", "search_frames", "try_embed_text"]
