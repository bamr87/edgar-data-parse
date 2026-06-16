"""Static site generator — a browsable, copy/download-friendly site of company
financials rendered from the warehouse (no live backend needed to view it).

Produces fully static HTML (one page per company + an index with client-side
search) plus per-company data files (``company.json`` and CSV exports). Reuses the
computation/profile services so the site shows exactly what the API does.
"""

from __future__ import annotations

import csv
import datetime
import io
import json
from pathlib import Path
from typing import Any, Iterable, cast

from django.template.loader import render_to_string

from warehouse.models import (
    Company,
    DerivedMetric,
    Fact,
    Filing,
    FilingDocument,
    LeadershipAnalysis,
    LeadershipPosition,
)
from warehouse.services.edgar.analytics import EdgarAnalyticsService
from warehouse.services.edgar.statements import (
    available_statement_types,
    build_financial_statement,
)

# Headline concepts shown in the per-company snapshot.
HEADLINE_CONCEPTS = [
    ("Revenues", "Revenue"),
    ("CostOfGoodsAndServicesSold", "Cost of Revenue"),
    ("OperatingIncomeLoss", "Operating Income"),
    ("NetIncomeLoss", "Net Income"),
    ("Assets", "Total Assets"),
    ("Liabilities", "Total Liabilities"),
    ("StockholdersEquity", "Stockholders' Equity"),
    ("CashAndCashEquivalentsAtCarryingValue", "Cash & Equivalents"),
]

STATEMENT_TITLES = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
    "cash_flow_statement": "Cash Flow Statement",
}

# How many fact rows to render inline (the full set is always downloadable).
FACT_PREVIEW_LIMIT = 100


def _cik_digits(cik: str) -> str:
    try:
        return str(int(cik))
    except (TypeError, ValueError):
        return cik


def sec_company_url(cik: str) -> str:
    return (
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
        f"&CIK={_cik_digits(cik)}&owner=exclude&count=40"
    )


def sec_filing_url(cik: str, accession: str) -> str:
    return (
        f"https://www.sec.gov/Archives/edgar/data/{_cik_digits(cik)}/"
        f"{accession.replace('-', '')}/"
    )


def fmt_value(value: Any, unit: str | None) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    u = (unit or "").lower()
    if u == "ratio":
        return f"{v:.4f}"
    if u == "pct" or u == "percent":
        return f"{v:.2%}"
    # USD, shares, or unspecified numeric -> grouped integer
    return f"{v:,.0f}"


def _rows_to_csv(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def build_company_context(company: Company) -> dict[str, Any]:
    """Assemble the display + data context for one company's page."""
    # Statements (latest period) with SEC links per line.
    statements = []
    for st in available_statement_types():
        s = build_financial_statement(company, st)
        rows = [
            {
                "label": li["label"],
                "value": li["value"],
                "value_display": fmt_value(li["value"], li["unit"]),
                "accession": li["accession"],
                "accession_url": sec_filing_url(company.cik, li["accession"])
                if li["accession"]
                else None,
            }
            for li in s["line_items"]
        ]
        statements.append(
            {
                "type": st,
                "title": STATEMENT_TITLES.get(st, st),
                "period_end": s["period_end"],
                "rows": rows,
            }
        )

    # Headline facts (latest per concept).
    latest = EdgarAnalyticsService.latest_by_concepts(
        company, [c for c, _ in HEADLINE_CONCEPTS]
    )
    headline = []
    for concept, label in HEADLINE_CONCEPTS:
        row = latest.get(concept)
        if row:
            headline.append(
                {
                    "label": label,
                    "concept": concept,
                    "value_display": fmt_value(row["value"], row["unit"]),
                    "period_end": row["period_end"],
                    "unit": row["unit"],
                }
            )

    # Derived metrics (latest per key).
    metric_rows: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for m in (
        DerivedMetric.objects.filter(company=company)
        .order_by("key", "-period_end")
        .values("key", "period_end", "value", "unit")
    ):
        if m["key"] in seen_keys:
            continue
        seen_keys.add(m["key"])
        metric_rows.append(
            {
                "key": m["key"],
                "period_end": str(m["period_end"]) if m["period_end"] else "",
                "value": str(m["value"]) if m["value"] is not None else "",
                "value_display": fmt_value(m["value"], m["unit"]),
                "unit": m["unit"],
            }
        )

    filings = [
        cast("dict[str, Any]", f)
        for f in Filing.objects.filter(company=company)
        .order_by("-filing_date")
        .values("form_type", "filing_date", "accession_number", "period_of_report")[:50]
    ]
    for f in filings:
        f["filing_date"] = str(f["filing_date"]) if f["filing_date"] else ""
        f["period_of_report"] = str(f["period_of_report"]) if f["period_of_report"] else ""
        f["url"] = sec_filing_url(company.cik, f["accession_number"])

    documents = [
        {
            "type": d.type,
            "file_name": d.file_name,
            "content_type": d.content_type,
            "snippet": (d.text or "")[:240],
        }
        for d in FilingDocument.objects.filter(filing__company=company).order_by(
            "-filing__filing_date", "sequence"
        )[:25]
    ]

    fact_preview = [
        cast("dict[str, Any]", fct)
        for fct in Fact.objects.filter(company=company)
        .order_by("-period_end", "concept")
        .values("concept", "taxonomy", "period_start", "period_end", "unit", "value")[
            :FACT_PREVIEW_LIMIT
        ]
    ]
    for fct in fact_preview:
        fct["period_start"] = str(fct["period_start"]) if fct["period_start"] else ""
        fct["period_end"] = str(fct["period_end"]) if fct["period_end"] else ""
        fct["value_display"] = fmt_value(fct["value"], fct["unit"])
        fct["value"] = str(fct["value"]) if fct["value"] is not None else ""

    # Leadership (officers/directors from SEC ownership filings) + stakeholder signals.
    leadership = [
        {
            "name": p.person.full_name,
            "title": p.title or ("Director" if p.is_director else "Insider"),
            "roles": ", ".join(
                r for r, on in (
                    ("Officer", p.is_officer), ("Director", p.is_director),
                    ("10% owner", p.is_ten_percent_owner),
                ) if on
            ),
            "first_seen": str(p.first_seen) if p.first_seen else "",
            "last_seen": str(p.last_seen) if p.last_seen else "",
            "net_insider_shares": float(p.net_insider_shares),
        }
        for p in LeadershipPosition.objects.filter(company=company)
        .select_related("person")
        .order_by("-filings_count")[:25]
    ]
    try:
        from warehouse.services.stakeholder import compute_stakeholder_assessment

        stakeholder = compute_stakeholder_assessment(company, persist=False)
    except Exception:  # pragma: no cover - analysis is best-effort for the static page
        stakeholder = None

    # Optional AI leadership narrative — render the latest stored analysis only if it
    # actually produced grounded content (the analyzer is off by default).
    la = (
        LeadershipAnalysis.objects.filter(company=company, enabled=True)
        .order_by("-created_at")
        .first()
    )
    leadership_analysis = None
    if la and (la.summary or la.initiatives or la.quotes or la.direction):
        leadership_analysis = {
            "summary": la.summary,
            "direction": la.direction,
            "initiatives": la.initiatives,
            "quotes": la.quotes,
            "model_name": la.model_name,
        }

    counts = {
        "facts": Fact.objects.filter(company=company).count(),
        "filings": Filing.objects.filter(company=company).count(),
        "documents": FilingDocument.objects.filter(filing__company=company).count(),
        "metrics": DerivedMetric.objects.filter(company=company).count(),
        "leadership": len(leadership),
    }
    sync = getattr(company, "edgar_sync", None)
    facts_as_of = (
        sync.facts_synced_at.date().isoformat() if sync and sync.facts_synced_at else None
    )
    identifiers = list(company.identifiers.values("system", "value")) if hasattr(
        company, "identifiers"
    ) else []

    return {
        "company": {
            "cik": company.cik,
            "ticker": company.ticker,
            "name": company.name,
            "sic_code": company.sic_code,
            "sic_description": company.sic_description,
            "industry": company.industry,
            "hq": ", ".join(
                [p for p in (company.hq_city, company.hq_state, company.hq_country) if p]
            )
            or (company.headquarters or ""),
            "sec_url": sec_company_url(company.cik),
            "identifiers": identifiers,
        },
        "headline": headline,
        "statements": statements,
        "metrics": metric_rows,
        "leadership": leadership,
        "stakeholder": stakeholder,
        "leadership_analysis": leadership_analysis,
        "filings": filings,
        "documents": documents,
        "fact_preview": fact_preview,
        "fact_preview_limit": FACT_PREVIEW_LIMIT,
        "counts": counts,
        "facts_as_of": facts_as_of,
        "downloads": [
            {"label": "Full profile (JSON)", "href": "company.json"},
            {"label": "XBRL facts (CSV)", "href": "facts.csv"},
            {"label": "Derived metrics (CSV)", "href": "metrics.csv"},
            {"label": "Statements (CSV)", "href": "statements.csv"},
            {"label": "Filings (CSV)", "href": "filings.csv"},
        ],
    }


def _write_company_data_files(company: Company, ctx: dict[str, Any], cdir: Path) -> None:
    # Full profile JSON (the API /profile/ payload + computed context).
    (cdir / "company.json").write_text(
        json.dumps({"company": ctx["company"], "counts": ctx["counts"],
                    "statements": ctx["statements"], "metrics": ctx["metrics"],
                    "leadership": ctx["leadership"], "stakeholder": ctx["stakeholder"],
                    "leadership_analysis": ctx["leadership_analysis"],
                    "filings": ctx["filings"], "documents": ctx["documents"],
                    "facts_as_of": ctx["facts_as_of"]}, indent=2, default=str),
        encoding="utf-8",
    )
    # Leadership CSV.
    if ctx["leadership"]:
        (cdir / "leadership.csv").write_text(
            _rows_to_csv(
                ["name", "title", "roles", "first_seen", "last_seen", "net_insider_shares"],
                ctx["leadership"],
            ),
            encoding="utf-8",
        )
    # Metrics CSV.
    (cdir / "metrics.csv").write_text(
        _rows_to_csv(
            ["key", "period_end", "value", "unit"],
            [
                {"key": m["key"], "period_end": m["period_end"], "value": m["value"], "unit": m["unit"]}
                for m in ctx["metrics"]
            ],
        ),
        encoding="utf-8",
    )
    # Statements CSV (flattened).
    stmt_rows = [
        {"statement": s["type"], "period_end": s["period_end"], "line_item": r["label"],
         "value": r["value"], "accession": r["accession"]}
        for s in ctx["statements"]
        for r in s["rows"]
    ]
    (cdir / "statements.csv").write_text(
        _rows_to_csv(["statement", "period_end", "line_item", "value", "accession"], stmt_rows),
        encoding="utf-8",
    )
    # Filings CSV.
    (cdir / "filings.csv").write_text(
        _rows_to_csv(
            ["form_type", "filing_date", "accession_number", "period_of_report"],
            [
                {k: f[k] for k in ("form_type", "filing_date", "accession_number", "period_of_report")}
                for f in ctx["filings"]
            ],
        ),
        encoding="utf-8",
    )
    # Facts CSV — the full set (can be large), streamed from the DB.
    fact_qs = (
        Fact.objects.filter(company=company)
        .order_by("-period_end", "concept")
        .values("concept", "taxonomy", "period_start", "period_end", "unit", "value")
    )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["concept", "taxonomy", "period_start", "period_end", "unit", "value"])
    for fct in fact_qs.iterator(chunk_size=2000):
        w.writerow([
            fct["concept"], fct["taxonomy"], fct["period_start"] or "",
            fct["period_end"] or "", fct["unit"] or "",
            fct["value"] if fct["value"] is not None else "",
        ])
    (cdir / "facts.csv").write_text(buf.getvalue(), encoding="utf-8")


def generate_site(
    companies: Iterable[Company],
    output_dir: str | Path,
    *,
    generated_at: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Render a full static site for ``companies`` into ``output_dir``.

    Returns a summary dict (counts + output path).
    """
    out = Path(output_dir)
    (out / "companies").mkdir(parents=True, exist_ok=True)
    stamp = (generated_at or datetime.datetime.now(datetime.timezone.utc)).date().isoformat()

    index_rows: list[dict[str, Any]] = []
    pages = 0
    for company in companies:
        ctx = build_company_context(company)
        ctx["generated_at"] = stamp
        cdir = out / "companies" / company.cik
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "index.html").write_text(
            render_to_string("staticsite/company.html", ctx), encoding="utf-8"
        )
        _write_company_data_files(company, ctx, cdir)
        index_rows.append(
            {
                "cik": company.cik,
                "ticker": company.ticker or "",
                "name": company.name,
                "sic_code": company.sic_code or "",
                "sic_description": company.sic_description or "",
                "hq": ctx["company"]["hq"],
                "facts": ctx["counts"]["facts"],
                "filings": ctx["counts"]["filings"],
                "href": f"companies/{company.cik}/index.html",
            }
        )
        pages += 1

    index_rows.sort(key=lambda r: r["name"].lower())
    (out / "index.html").write_text(
        render_to_string(
            "staticsite/index.html", {"companies": index_rows, "generated_at": stamp}
        ),
        encoding="utf-8",
    )
    (out / "companies.json").write_text(
        json.dumps(index_rows, indent=2, default=str), encoding="utf-8"
    )
    (out / "companies.csv").write_text(
        _rows_to_csv(
            ["cik", "ticker", "name", "sic_code", "sic_description", "hq", "facts", "filings"],
            index_rows,
        ),
        encoding="utf-8",
    )
    return {"pages": pages, "output_dir": str(out), "generated_at": stamp}
