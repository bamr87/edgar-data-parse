"""Static site generation (the 'Wikipedia of company financials')."""

from __future__ import annotations

import datetime
import decimal
import json

import pytest
from django.core.management import call_command

from warehouse.models import Company, DerivedMetric, Fact, Filing, FilingDocument
from warehouse.services.static_site import build_company_context, fmt_value, generate_site

FY = {"period_start": datetime.date(2023, 1, 1), "period_end": datetime.date(2023, 12, 31)}


@pytest.fixture
def company(db):
    co = Company.objects.create(
        cik="0000320193", ticker="AAPL", name="Apple Inc.",
        sic_code="3571", sic_description="Electronic Computers", hq_state="CA",
    )
    Fact.objects.create(
        company=co, taxonomy="us-gaap", concept="Revenues",
        value=decimal.Decimal("383285000000"), dimensions={"accn": "0000320193-23-000106"}, **FY
    )
    Fact.objects.create(
        company=co, taxonomy="us-gaap", concept="CostOfGoodsAndServicesSold",
        value=decimal.Decimal("214137000000"), **FY
    )
    Fact.objects.create(
        company=co, taxonomy="us-gaap", concept="NetIncomeLoss",
        value=decimal.Decimal("96995000000"), **FY
    )
    DerivedMetric.objects.create(
        company=co, key="gross_margin", period_end=FY["period_end"],
        value=decimal.Decimal("0.441"), unit="ratio"
    )
    f = Filing.objects.create(
        company=co, accession_number="0000320193-23-000106", form_type="10-K",
        filing_date=FY["period_end"],
    )
    FilingDocument.objects.create(
        filing=f, sequence=1, sha1="x", type="10-K", file_name="aapl.htm",
        content_type="text/html", text="Apple annual report discussion.",
    )
    return co


def test_fmt_value():
    assert fmt_value(383285000000, "USD") == "383,285,000,000"
    assert fmt_value(decimal.Decimal("0.441"), "ratio") == "0.4410"
    assert fmt_value(None, "USD") == "—"


@pytest.mark.django_db
def test_build_company_context(company):
    ctx = build_company_context(company)
    assert ctx["company"]["ticker"] == "AAPL"
    assert ctx["company"]["hq"] == "CA, US"
    assert ctx["counts"]["facts"] == 3
    assert any(h["label"] == "Revenue" for h in ctx["headline"])
    assert any(m["key"] == "gross_margin" for m in ctx["metrics"])
    income = next(s for s in ctx["statements"] if s["type"] == "income_statement")
    assert any(r["label"] == "Revenue" and r["value"] == 383285000000.0 for r in income["rows"])
    # statement line links to the source filing
    assert any(r["accession"] == "0000320193-23-000106" for r in income["rows"])


@pytest.mark.django_db
def test_generate_site_files(company, tmp_path):
    summary = generate_site([company], tmp_path)
    assert summary["pages"] == 1

    index_html = (tmp_path / "index.html").read_text()
    assert "Apple Inc." in index_html
    assert "companies.csv" in index_html  # site-wide download link

    cdir = tmp_path / "companies" / company.cik
    page = (cdir / "index.html").read_text()
    assert "Apple Inc." in page
    assert "Income Statement" in page
    assert "gross_margin" in page
    assert 'href="facts.csv"' in page  # download affordance
    assert "copyTable(" in page  # copy affordance
    assert "383,285,000,000" in page  # formatted headline value

    data = json.loads((cdir / "company.json").read_text())
    assert data["company"]["cik"] == company.cik
    assert data["counts"]["facts"] == 3

    facts_csv = (cdir / "facts.csv").read_text()
    assert facts_csv.startswith("concept,taxonomy,")
    assert "Revenues" in facts_csv

    metrics_csv = (cdir / "metrics.csv").read_text()
    assert "gross_margin" in metrics_csv
    assert (cdir / "statements.csv").exists()
    assert (cdir / "filings.csv").exists()

    assert (tmp_path / "companies.json").exists()
    assert (tmp_path / "companies.csv").read_text().startswith("cik,ticker,name,")


@pytest.mark.django_db
def test_generate_static_site_command(company, tmp_path):
    call_command("generate_static_site", "--ticker", "AAPL", "--output", str(tmp_path))
    assert (tmp_path / "companies" / company.cik / "index.html").exists()
    assert (tmp_path / "index.html").exists()


@pytest.mark.django_db
def test_generate_site_publishing_extras(company, tmp_path):
    """GitHub Pages needs .nojekyll; base_url enables sitemap/robots; app_url cross-links."""
    generate_site(
        [company],
        tmp_path,
        base_url="https://example.github.io/fredgar-ai",
        app_url="https://app.example.com",
    )
    assert (tmp_path / ".nojekyll").exists()

    about = (tmp_path / "about.html").read_text()
    assert "static mirror" in about
    assert "https://app.example.com/" in about  # cross-link to the interactive app

    sitemap = (tmp_path / "sitemap.xml").read_text()
    assert f"https://example.github.io/fredgar-ai/companies/{company.cik}/index.html" in sitemap
    assert "about.html" in sitemap
    robots = (tmp_path / "robots.txt").read_text()
    assert "Sitemap: https://example.github.io/fredgar-ai/sitemap.xml" in robots

    # Company pages resolve site-root links via the ../../ prefix.
    page = (tmp_path / "companies" / company.cik / "index.html").read_text()
    assert '../../about.html' in page


@pytest.mark.django_db
def test_generate_site_without_base_url_skips_seo_files(company, tmp_path):
    generate_site([company], tmp_path, base_url="", app_url="", source_url="")
    assert (tmp_path / ".nojekyll").exists()
    assert not (tmp_path / "sitemap.xml").exists()
    assert not (tmp_path / "robots.txt").exists()


@pytest.mark.django_db
def test_publish_static_site_command_skip_sync(company, tmp_path):
    """--skip-sync renders from warehouse data with no SEC calls; unknown tickers are reported."""
    call_command(
        "publish_static_site",
        "--skip-sync",
        "--tickers", "AAPL,ZZZZ",
        "--output", str(tmp_path),
        "--base-url", "https://example.github.io/fredgar-ai",
    )
    assert (tmp_path / "companies" / company.cik / "index.html").exists()
    assert (tmp_path / "about.html").exists()
    assert (tmp_path / "sitemap.xml").exists()


@pytest.mark.django_db
def test_publish_static_site_command_fails_when_nothing_publishable(tmp_path):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command(
            "publish_static_site", "--skip-sync", "--tickers", "ZZZZ",
            "--output", str(tmp_path),
        )


@pytest.mark.django_db
def test_publish_site_tolerates_per_ticker_sync_failures(company, tmp_path, monkeypatch):
    """One ticker failing to sync must not abort the publish of the others."""
    from warehouse.services import static_site_publish

    def fake_sync(ticker, **kwargs):
        if ticker == "FAIL":
            raise RuntimeError("SEC unavailable")
        return company

    monkeypatch.setattr(static_site_publish, "sync_company_for_site", fake_sync)
    summary = static_site_publish.publish_site(["FAIL", "AAPL"], tmp_path, delay=0)
    assert summary["companies"] == 1
    assert "SEC unavailable" in summary["errors"]["FAIL"]
    assert (tmp_path / "companies" / company.cik / "index.html").exists()
