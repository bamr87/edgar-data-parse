"""Apply SEC title index to CrmCompanyRecord rows."""

from __future__ import annotations

import logging

from sec_edgar.services.crm_sec_match import build_title_index, lookup_issuer_for_crm_name
from warehouse.models import CrmCompanyRecord

logger = logging.getLogger(__name__)


def _names_for_record(rec: CrmCompanyRecord) -> list[str]:
    out: list[str] = []
    for v in (rec.unique_name, rec.contract_name, rec.global_hq_name, rec.name):
        if v and str(v).strip():
            out.append(str(v).strip())
    seen: set[str] = set()
    uniq: list[str] = []
    for n in out:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(n)
    return uniq


def match_crm_records_to_sec(
    *,
    user_agent_email: str | None,
    reset: bool = False,
) -> dict[str, int]:
    index = build_title_index(user_agent_email=user_agent_email)
    qs = CrmCompanyRecord.objects.all()
    if reset:
        qs.update(
            sec_cik=None,
            sec_ticker=None,
            match_status=None,
            match_note=None,
        )

    exact = ambiguous = none = 0
    to_update: list[CrmCompanyRecord] = []

    for rec in CrmCompanyRecord.objects.iterator(chunk_size=800):
        chosen_cik = None
        chosen_ticker = None
        status = "none"
        note = ""
        ambiguous_note: str | None = None
        for nm in _names_for_record(rec):
            cik, ticker, st = lookup_issuer_for_crm_name(nm, index)
            if st == "exact":
                chosen_cik = cik
                chosen_ticker = ticker
                status = "exact"
                note = f"matched:{nm[:80]}"
                break
            if st == "ambiguous" and ambiguous_note is None:
                ambiguous_note = nm[:80]
        if status != "exact" and ambiguous_note is not None:
            status = "ambiguous"
            note = f"ambiguous:{ambiguous_note}"
        if status == "ambiguous":
            ambiguous += 1
            rec.sec_cik = None
            rec.sec_ticker = None
            rec.match_status = "ambiguous"
            rec.match_note = note[:255]
            to_update.append(rec)
        elif status == "exact" and chosen_cik:
            exact += 1
            rec.sec_cik = chosen_cik
            rec.sec_ticker = (chosen_ticker or "")[:16] or None
            rec.match_status = "exact"
            rec.match_note = note[:255]
            to_update.append(rec)
        else:
            none += 1
            rec.sec_cik = None
            rec.sec_ticker = None
            rec.match_status = "unmatched"
            rec.match_note = ""
            to_update.append(rec)

        if len(to_update) >= 400:
            CrmCompanyRecord.objects.bulk_update(
                to_update,
                ["sec_cik", "sec_ticker", "match_status", "match_note"],
            )
            to_update.clear()

    if to_update:
        CrmCompanyRecord.objects.bulk_update(
            to_update,
            ["sec_cik", "sec_ticker", "match_status", "match_note"],
        )

    logger.info("CRM SEC title match: exact=%s ambiguous=%s unmatched=%s", exact, ambiguous, none)
    return {"exact": exact, "ambiguous": ambiguous, "unmatched": none}
