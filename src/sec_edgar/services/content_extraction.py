"""Extract plain text from filing document content.

HTML/plain text are handled in-process with BeautifulSoup. Other formats (PDF,
etc.) are routed to an Apache Tika server when ``ENABLE_TIKA`` is set — Tika is a
Java sidecar (see docker-compose ``tika`` service) reached over HTTP.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)


def _html_to_text(content: str) -> str:
    soup = BeautifulSoup(content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _tika_extract(content: bytes) -> str:
    """Extract via Tika server (lazy import; only when ENABLE_TIKA)."""
    from tika import parser as tika_parser  # noqa: PLC0415

    endpoint = getattr(settings, "TIKA_SERVER_ENDPOINT", None)
    parsed = tika_parser.from_buffer(content, serverEndpoint=endpoint)
    return (parsed.get("content") or "").strip()


def extract_text(content: str, content_type: str | None) -> str:
    """Return plain text for ``content`` given its ``content_type``.

    HTML -> BeautifulSoup; plain text -> as-is; everything else -> Tika when
    enabled, otherwise an empty string (the raw bytes remain in object storage).
    """
    ctype = (content_type or "").lower()
    if "html" in ctype:
        return _html_to_text(content)
    if ctype.startswith("text/") or ctype in ("application/xml", ""):
        return content.strip()
    if getattr(settings, "ENABLE_TIKA", False):
        try:
            return _tika_extract(content.encode("utf-8", "ignore"))
        except Exception:  # pragma: no cover - depends on a running Tika server
            logger.exception("Tika extraction failed for content_type=%s", content_type)
            return ""
    return ""
