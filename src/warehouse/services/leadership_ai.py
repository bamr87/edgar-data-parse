"""Optional LLM narrative analyzer for company leadership.

Extracts leadership *initiatives*, *verbatim quotes*, and *stated forward direction*
from a company's SEC filing text — and ONLY from that text. The whole subsystem is
gated behind ``settings.ENABLE_AI_ANALYSIS`` (default off) and treats the Anthropic
SDK as a lazy optional dependency (``pip install -r requirements-ai.txt``), so the
core runtime never imports it.

Responsible-use boundary (enforced in ``SYSTEM_PROMPT`` and documented in
``docs/leadership-methodology.md``):
  * Every item must be grounded in a provided excerpt and cite its source label.
  * Quotes must be verbatim from an excerpt — the model never invents or paraphrases.
  * No personal, character, competence, or "approval" judgments about any individual.
This is narrative extraction with citations, not an opinion about people.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from django.conf import settings

from warehouse.models import (
    Company,
    ContentChunk,
    FilingDocument,
    LeadershipAnalysis,
)

logger = logging.getLogger(__name__)

# Bounds on what we send to the model (keep token cost + scope contained).
MAX_PASSAGES = 12
MAX_PASSAGE_CHARS = 2000
MAX_OUTPUT_TOKENS = 6000

# Structured-output schema. ``output_config.format`` guarantees the first content
# block is text containing JSON valid against this schema.
ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "2-4 sentence neutral summary of leadership initiatives and "
            "direction, grounded only in the excerpts.",
        },
        "initiatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {"type": "string", "description": "Source label, e.g. 'S2'."},
                },
                "required": ["title", "description", "source"],
                "additionalProperties": False,
            },
        },
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Verbatim quote from an excerpt."},
                    "speaker": {"type": "string"},
                    "source": {"type": "string", "description": "Source label, e.g. 'S3'."},
                },
                "required": ["text", "source"],
                "additionalProperties": False,
            },
        },
        "direction": {
            "type": "string",
            "description": "Stated forward direction/strategy, grounded only in the excerpts.",
        },
    },
    "required": ["summary", "initiatives", "quotes", "direction"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are a careful SEC-disclosure analyst. You receive excerpts from one company's "
    "SEC filings, each labeled [S1], [S2], etc. Extract ONLY what those excerpts "
    "explicitly support: leadership initiatives, direct quotes, and the stated forward "
    "direction.\n"
    "RULES (strict):\n"
    "1. Ground every item in the excerpts and cite the source label (e.g. \"S2\") in "
    "the `source` field. If something is not in the excerpts, omit it.\n"
    "2. A quote must appear VERBATIM in an excerpt. Never invent, paraphrase, or "
    "reconstruct quotes. If no verbatim quote exists, return an empty `quotes` list.\n"
    "3. Make NO personal, character, competence, popularity, or 'approval' judgments "
    "about any named individual. Describe disclosed company/leadership actions and "
    "plans, not anyone's worth.\n"
    "4. Use no outside knowledge and no speculation. Leave a field empty rather than "
    "guess.\n"
    "Return the structured analysis as specified."
)


class LeadershipAnalyzer(Protocol):
    """Strategy interface so the backend is swappable and testable."""

    enabled: bool
    backend: str
    model_name: str

    def analyze(self, company_name: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
        ...


class NoopAnalyzer:
    """Default analyzer when AI analysis is disabled — does no LLM call."""

    enabled = False
    backend = "none"
    model_name = ""

    def analyze(self, company_name: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "summary": "",
            "initiatives": [],
            "quotes": [],
            "direction": "",
            "note": "AI analysis is disabled (set ENABLE_AI_ANALYSIS=true and install "
            "requirements-ai.txt).",
        }


class AnthropicAnalyzer:
    """Anthropic-backed analyzer. SDK is imported lazily; ``client`` is injectable."""

    enabled = True
    backend = "anthropic"

    def __init__(self, *, client: Any | None = None, model: str | None = None) -> None:
        self.model_name: str = str(
            model or getattr(settings, "AI_ANALYSIS_MODEL", None) or "claude-opus-4-8"
        )
        self._client = client

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # lazy optional dependency
        except ImportError as e:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "AI analysis requires the 'anthropic' package. "
                "Install it with: pip install -r requirements-ai.txt"
            ) from e
        self._client = anthropic.Anthropic()
        return self._client

    def analyze(self, company_name: str, passages: list[dict[str, Any]]) -> dict[str, Any]:
        excerpts = "\n\n".join(
            f"[{p['tag']}] ({p.get('type') or 'doc'} {p.get('accession') or ''})\n{p['text']}"
            for p in passages
        )
        user_content = (
            f"Company: {company_name}\n\n"
            f"Excerpts from this company's SEC filings:\n\n{excerpts}\n\n"
            "Produce the structured leadership analysis. Cite source labels; quotes "
            "must be verbatim from the excerpts above."
        )
        resp = self._get_client().messages.create(
            model=self.model_name,
            max_tokens=MAX_OUTPUT_TOKENS,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_config={"format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA}},
        )
        # output_config.format guarantees a text block with schema-valid JSON.
        text = next(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return json.loads(text)


def get_leadership_analyzer(*, client: Any | None = None) -> LeadershipAnalyzer:
    """Return the configured analyzer (Noop unless AI analysis is enabled)."""
    if not getattr(settings, "ENABLE_AI_ANALYSIS", False):
        return NoopAnalyzer()
    backend = getattr(settings, "AI_ANALYSIS_BACKEND", "anthropic")
    if backend == "anthropic":
        return AnthropicAnalyzer(client=client)
    return NoopAnalyzer()


def _gather_passages(company: Company, *, limit: int = MAX_PASSAGES) -> list[dict[str, Any]]:
    """Collect grounded text passages for a company, tagged [S1], [S2], ….

    Prefers pre-chunked ``ContentChunk`` rows (the AI-ready substrate); falls back to
    raw ``FilingDocument`` text. Each passage carries its filing accession + document
    type so the model — and any reader — can trace a claim back to the source.
    """
    passages: list[dict[str, Any]] = []

    chunks = (
        ContentChunk.objects.filter(company=company)
        .select_related("filing_document__filing")
        .order_by("-fetched_at")[:limit]
    )
    for ch in chunks:
        fd = ch.filing_document
        filing = getattr(fd, "filing", None)
        passages.append(
            {
                "text": (ch.text or "")[:MAX_PASSAGE_CHARS],
                "accession": getattr(filing, "accession_number", "") if filing else "",
                "type": getattr(fd, "type", "") if fd else ch.source,
            }
        )

    if not passages:
        docs = (
            FilingDocument.objects.filter(filing__company=company)
            .exclude(text="")
            .select_related("filing")
            .order_by("-filing__filing_date", "sequence")[:limit]
        )
        for d in docs:
            passages.append(
                {
                    "text": (d.text or "")[:MAX_PASSAGE_CHARS],
                    "accession": d.filing.accession_number if d.filing_id else "",
                    "type": d.type or "",
                }
            )

    for i, p in enumerate(passages, start=1):
        p["tag"] = f"S{i}"
    return [p for p in passages if p["text"].strip()]


def analyze_company_leadership(
    company: Company, *, persist: bool = True, client: Any | None = None
) -> dict[str, Any]:
    """Run (or no-op) the LLM leadership analysis for a company.

    Returns a dict mirroring the persisted ``LeadershipAnalysis`` plus the passages
    used. Never raises on a model/SDK failure — records the error and returns a
    disabled-shaped result so callers (API, command, static site) degrade gracefully.
    """
    analyzer = get_leadership_analyzer(client=client)
    passages = _gather_passages(company)
    used_sources = [
        {"tag": p["tag"], "accession": p["accession"], "type": p["type"]} for p in passages
    ]

    base: dict[str, Any] = {
        "company": company.id,
        "enabled": analyzer.enabled,
        "backend": analyzer.backend,
        "model_name": getattr(analyzer, "model_name", ""),
        "summary": "",
        "initiatives": [],
        "quotes": [],
        "direction": "",
        "used_sources": used_sources,
        "error": "",
    }

    if not analyzer.enabled:
        result = analyzer.analyze(company.name, passages)
        base["note"] = result.get("note", "")
        if persist:
            _persist(company, base)
        return base

    if not passages:
        base["error"] = (
            "No filing text available to analyze. Ingest filing documents first "
            "(e.g. ingest_submission) so there is grounded text."
        )
        if persist:
            _persist(company, base)
        return base

    try:
        out = analyzer.analyze(company.name, passages)
        base["summary"] = out.get("summary", "")
        base["initiatives"] = out.get("initiatives", [])
        base["quotes"] = out.get("quotes", [])
        base["direction"] = out.get("direction", "")
    except Exception as e:  # noqa: BLE001 - degrade gracefully, record the error
        logger.warning("Leadership analysis failed for company %s: %s", company.id, e)
        base["error"] = str(e)[:1000]

    if persist:
        _persist(company, base)
    return base


def _persist(company: Company, data: dict[str, Any]) -> LeadershipAnalysis:
    return LeadershipAnalysis.objects.create(
        company=company,
        enabled=data["enabled"],
        summary=data["summary"],
        initiatives=data["initiatives"],
        quotes=data["quotes"],
        direction=data["direction"],
        used_sources=data["used_sources"],
        backend=data["backend"],
        model_name=data["model_name"],
        error=data["error"],
    )
