"""Chunk filing text into retrievable ``ContentChunk`` rows (AI foundation).

Chunking is a pure function; embedding is delegated to a pluggable backend that
defaults to a no-op (``ENABLE_EMBEDDINGS=false``). The schema + retrieval exist
regardless, so a real embedder can be enabled later with no migration.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Protocol

from django.conf import settings

from warehouse.models import ContentChunk, FilingDocument

logger = logging.getLogger(__name__)


def chunk_text(text: str, *, size: int = 1000, overlap: int = 100) -> Iterator[tuple[int, int, str]]:
    """Yield ``(char_start, char_end, chunk)`` windows over ``text``."""
    text = text or ""
    if not text.strip():
        return
    step = max(1, size - overlap)
    for start in range(0, len(text), step):
        end = min(len(text), start + size)
        yield start, end, text[start:end]
        if end >= len(text):
            break


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float] | None]: ...


class NoopEmbedder:
    """Default embedder — produces no vectors (keyword search still works)."""

    name = "none"

    def embed(self, texts: list[str]) -> list[list[float] | None]:
        return [None for _ in texts]


def get_embedder() -> Embedder:
    if not getattr(settings, "ENABLE_EMBEDDINGS", False):
        return NoopEmbedder()
    backend = getattr(settings, "EMBEDDINGS_BACKEND", "none")
    # 'local' / 'api' backends are deferred; wiring one in needs only a class here.
    if backend != "none":
        logger.warning(
            "ENABLE_EMBEDDINGS is on but EMBEDDINGS_BACKEND=%r is not implemented yet; "
            "falling back to NoopEmbedder (no vectors written).",
            backend,
        )
    return NoopEmbedder()


def index_filing_document(
    doc: FilingDocument, *, size: int = 1000, overlap: int = 100
) -> int:
    """(Re)chunk a FilingDocument's extracted text into ContentChunk rows."""
    ContentChunk.objects.filter(filing_document=doc).delete()
    windows = list(chunk_text(doc.text, size=size, overlap=overlap))
    if not windows:
        return 0
    embedder = get_embedder()
    vectors = embedder.embed([c for _, _, c in windows])
    rows = [
        ContentChunk(
            company_id=doc.filing.company_id,
            filing_document=doc,
            source="filing_document",
            char_start=start,
            char_end=end,
            text=chunk,
            embedding=vector,
            embedding_model=embedder.name if vector is not None else "",
        )
        for (start, end, chunk), vector in zip(windows, vectors)
    ]
    ContentChunk.objects.bulk_create(rows)
    return len(rows)
