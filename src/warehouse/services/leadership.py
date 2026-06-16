"""Extract company leadership (officers/directors/owners) from SEC Forms 3/4/5.

Factual extraction only — names, titles, role flags, filing-date tenure bounds, and
net insider share activity, all from legally public SEC ownership filings. External
enrichment (e.g. licensed profile data) is a separate, opt-in provider — never scraped.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal

from sec_edgar.cik import normalize_cik
from sec_edgar.parsers.ownership import parse_ownership
from sec_edgar.parsers.submission import parse_submission
from warehouse.models import Company, Filing, LeadershipPosition, Person

logger = logging.getLogger(__name__)

OWNERSHIP_FORMS = ["3", "4", "5", "3/A", "4/A", "5/A"]


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def _resolve_person(cik: str | None, name: str) -> Person:
    norm = normalize_name(name)
    if cik:
        try:
            cik = normalize_cik(cik)
        except ValueError:
            cik = None
    if cik:
        person, created = Person.objects.get_or_create(
            cik=cik, defaults={"full_name": name, "normalized_name": norm}
        )
        if not created and not person.full_name and name:
            person.full_name = name
            person.save(update_fields=["full_name", "updated_at"])
        return person
    person, _ = Person.objects.get_or_create(
        normalized_name=norm, cik=None, defaults={"full_name": name}
    )
    return person


def upsert_owner(
    company: Company,
    owner: dict,
    *,
    filing_date=None,
    net_shares: float = 0.0,
    source_url: str = "",
) -> tuple[Person, LeadershipPosition, bool]:
    """Upsert a Person + their LeadershipPosition at a company from a parsed owner."""
    person = _resolve_person(owner.get("cik"), owner.get("name") or "")
    pos, created = LeadershipPosition.objects.get_or_create(
        person=person, company=company, defaults={"first_seen": filing_date, "last_seen": filing_date}
    )
    if owner.get("officer_title"):
        pos.title = owner["officer_title"][:255]
    pos.is_director = pos.is_director or owner.get("is_director", False)
    pos.is_officer = pos.is_officer or owner.get("is_officer", False)
    pos.is_ten_percent_owner = pos.is_ten_percent_owner or owner.get("is_ten_percent_owner", False)
    if filing_date:
        pos.first_seen = min(pos.first_seen or filing_date, filing_date)
        pos.last_seen = max(pos.last_seen or filing_date, filing_date)
    pos.filings_count += 1
    pos.net_insider_shares = (pos.net_insider_shares or Decimal(0)) + Decimal(str(net_shares))
    if source_url:
        pos.source_url = source_url[:512]
    pos.save()
    return person, pos, created


def _find_ownership_xml(buffer: str) -> str | None:
    for doc in parse_submission(buffer):
        if "<ownershipDocument" in doc["content"]:
            return doc["content"]
    return None


def sync_leadership(
    company: Company, *, user_agent_email: str | None = None, limit: int = 25
) -> dict:
    """Fetch recent Forms 3/4/5 for a company and extract leadership positions.

    Bounded by ``limit`` to respect SEC fair-access. Reuses the submission fetch +
    parser, so no new SEC endpoints are touched.
    """
    from sec_edgar.client import SecEdgarClient

    client = SecEdgarClient(user_agent_email=user_agent_email)
    cik_digits = normalize_cik(company.cik).lstrip("0") or company.cik
    filings = (
        Filing.objects.filter(company=company, form_type__in=OWNERSHIP_FORMS)
        .order_by("-filing_date")[:limit]
    )
    processed = 0
    for f in filings:
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_digits}/{f.accession_number}.txt"
        try:
            buffer = client.get_text(url)
        except Exception:
            logger.warning("Could not fetch ownership filing %s", f.accession_number)
            continue
        xml = _find_ownership_xml(buffer)
        if not xml:
            continue
        try:
            parsed = parse_ownership(xml)
        except Exception:
            continue
        for owner in parsed["owners"]:
            upsert_owner(
                company, owner, filing_date=f.filing_date,
                net_shares=parsed["net_shares"], source_url=url,
            )
        processed += 1
    return {
        "filings_processed": processed,
        "people": Person.objects.filter(positions__company=company).distinct().count(),
        "positions": LeadershipPosition.objects.filter(company=company).count(),
    }
