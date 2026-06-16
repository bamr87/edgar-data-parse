"""Ingest a full SEC submission (.txt) into Filing + FilingDocument rows.

Two levels:
- :func:`ingest_submission_documents` — parse a buffer into FilingDocument rows,
  storing raw bytes (content-addressed) and extracting text. Pure of network I/O.
- :func:`ingest_submission` — resolve the company/filing and fetch the buffer from
  SEC, then delegate to the above. This generalizes single-HTM ``ingest_htm``.
"""

from __future__ import annotations

import logging

from django.db import transaction

from sec_edgar.cik import normalize_cik
from sec_edgar.parsers.submission import parse_submission, submission_header_field
from sec_edgar.services.content_extraction import extract_text
from sec_edgar.storage import Storage, get_storage, store_content
from warehouse.models import Company, Filing, FilingDocument

logger = logging.getLogger(__name__)

_MAX_TEXT = 5_000_000  # guard against pathological exhibit sizes in the DB column


@transaction.atomic
def ingest_submission_documents(
    filing: Filing,
    buffer: str,
    *,
    extract: bool = True,
    chunk: bool = True,
    storage: Storage | None = None,
) -> int:
    """Parse ``buffer`` into FilingDocument rows for ``filing``; returns the count.

    When ``chunk`` is set, each document's extracted text is chunked into
    ``ContentChunk`` rows (the Company-360 retrieval substrate).
    """
    from warehouse.services.chunks import index_filing_document

    storage = storage or get_storage()
    count = 0
    for doc in parse_submission(buffer):
        raw_key = store_content(
            doc["content"].encode("utf-8", "ignore"), prefix="raw", storage=storage
        )
        text = extract_text(doc["content"], doc["content_type"]) if extract else ""
        filing_document, _ = FilingDocument.objects.update_or_create(
            filing=filing,
            sequence=doc["sequence"],
            defaults={
                "type": doc["type"],
                "file_name": doc["file_name"],
                "content_type": doc["content_type"],
                "description": doc["description"],
                "sha1": doc["sha1"],
                "raw_key": raw_key,
                "text": text[:_MAX_TEXT],
                "start_pos": doc["start_pos"],
                "end_pos": doc["end_pos"],
                "is_processed": True,
                "is_error": False,
            },
        )
        if chunk and text:
            index_filing_document(filing_document)
        count += 1
    return count


def _resolve_company(
    ticker: str | None, cik: str | None, user_agent_email: str | None
) -> Company:
    if cik:
        norm = normalize_cik(cik)
        company, _ = Company.objects.get_or_create(
            cik=norm, defaults={"ticker": (ticker or "").upper() or None, "name": norm}
        )
        return company
    if ticker:
        from sec_edgar.adapters.direct import DirectEdgarAdapter

        info = DirectEdgarAdapter(user_agent_email=user_agent_email).cik_for_ticker(ticker)
        company, _ = Company.objects.get_or_create(
            cik=info["cik"], defaults={"ticker": ticker.upper(), "name": info["name"]}
        )
        return company
    raise ValueError("ticker or cik required")


def ingest_submission(
    *,
    url: str,
    ticker: str | None = None,
    cik: str | None = None,
    accession: str | None = None,
    user_agent_email: str | None = None,
    extract: bool = True,
) -> tuple[Filing, int]:
    """Fetch a submission .txt, resolve its Filing, and ingest its documents."""
    from sec_edgar.client import SecEdgarClient

    company = _resolve_company(ticker, cik, user_agent_email)
    buffer = SecEdgarClient(user_agent_email=user_agent_email).get_text(url)
    acc = (
        accession
        or submission_header_field(buffer, "ACCESSION NUMBER")
        or url.rstrip("/").rsplit("/", 1)[-1].replace(".txt", "")
    )
    form_type = submission_header_field(buffer, "CONFORMED SUBMISSION TYPE") or "UNKNOWN"
    filing, _ = Filing.objects.update_or_create(
        company=company,
        accession_number=str(acc)[:30],
        defaults={"form_type": form_type[:20], "url": url},
    )
    count = ingest_submission_documents(filing, buffer, extract=extract)
    logger.info("Ingested %d documents for filing=%s", count, filing.accession_number)
    return filing, count
