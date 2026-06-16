"""Parse a full SEC submission (.txt) into its constituent ``<DOCUMENT>`` sections.

A submission is SGML: a ``<SEC-HEADER>`` followed by one or more ``<DOCUMENT>``
blocks, each with ``<TYPE>``/``<SEQUENCE>``/``<FILENAME>``/``<DESCRIPTION>`` header
lines and a ``<TEXT>...</TEXT>`` body (HTML, plain text, or uuencoded binary).

The decomposition approach is adapted from LexPredict OpenEDGAR's
``openedgar/parsers/edgar.py`` (MIT License, Copyright (c) 2018 ContraxSuite, LLC),
reimplemented here for this project's models and storage.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator

_DOCUMENT_RE = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.DOTALL | re.IGNORECASE)
_TEXT_RE = re.compile(r"<TEXT>(.*?)</TEXT>", re.DOTALL | re.IGNORECASE)


def _header_field(block: str, tag: str) -> str | None:
    # SGML header lines look like ``<TYPE>10-K`` (value runs to end of line).
    m = re.search(rf"<{tag}>([^\n<\r]*)", block, re.IGNORECASE)
    return m.group(1).strip() or None if m else None


def _content_type_for(file_name: str | None, content: str) -> str:
    name = (file_name or "").lower()
    if name.endswith((".htm", ".html")):
        return "text/html"
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith((".txt", ".text")):
        return "text/plain"
    if name.endswith((".xml", ".xsd")):
        return "application/xml"
    # Fall back to sniffing the leading content.
    head = content.lstrip()[:200].lower()
    if head.startswith("<html") or "<!doctype html" in head or "<body" in head:
        return "text/html"
    return "text/plain"


def parse_submission(buffer: str) -> Iterator[dict]:
    """Yield one dict per ``<DOCUMENT>`` block.

    Keys: ``type``, ``sequence``, ``file_name``, ``description``, ``content_type``,
    ``content`` (the raw ``<TEXT>`` body), ``sha1``, ``start_pos``, ``end_pos``.
    """
    for index, match in enumerate(_DOCUMENT_RE.finditer(buffer)):
        block = match.group(1)
        text_match = _TEXT_RE.search(block)
        content = text_match.group(1).strip() if text_match else ""
        seq_raw = _header_field(block, "SEQUENCE")
        sequence = int(seq_raw) if seq_raw and seq_raw.isdigit() else index
        file_name = _header_field(block, "FILENAME")
        sha1 = hashlib.sha1(content.encode("utf-8", "ignore")).hexdigest()
        yield {
            "type": _header_field(block, "TYPE"),
            "sequence": sequence,
            "file_name": file_name,
            "description": _header_field(block, "DESCRIPTION"),
            "content_type": _content_type_for(file_name, content),
            "content": content,
            "sha1": sha1,
            "start_pos": match.start(),
            "end_pos": match.end(),
        }


def submission_header_field(buffer: str, field: str) -> str | None:
    """Read a value from the ``<SEC-HEADER>`` block (e.g. ACCESSION NUMBER, CIK)."""
    header_end = buffer.find("</SEC-HEADER>")
    header = buffer[:header_end] if header_end != -1 else buffer[:5000]
    m = re.search(rf"{re.escape(field)}:\s*([^\n\r]*)", header, re.IGNORECASE)
    return m.group(1).strip() or None if m else None
