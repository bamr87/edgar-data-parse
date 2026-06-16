"""Parse SEC ownership filings (Forms 3/4/5 ``<ownershipDocument>`` XML).

Extracts the issuer, the reporting owner(s) with their role flags/titles, and a net
acquired(+)/disposed(-) share total (an insider-alignment signal). These are
legally public, SEC-disclosed facts about company insiders.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

_TRUE = {"1", "true", "y", "yes"}


def _text(el, path: str) -> str | None:
    if el is None:
        return None
    node = el.find(path)
    if node is None or node.text is None:
        return None
    return node.text.strip() or None


def _flag(rel, tag: str) -> bool:
    v = _text(rel, tag)
    if not v:
        return False
    return v.lower() in _TRUE


def parse_ownership(xml_text: str) -> dict:
    """Parse an ownership document. Raises ``ValueError`` if not one."""
    start = xml_text.find("<ownershipDocument")
    end = xml_text.rfind("</ownershipDocument>")
    if start == -1 or end == -1:
        raise ValueError("no <ownershipDocument> found")
    root = ET.fromstring(xml_text[start : end + len("</ownershipDocument>")])

    issuer = {
        "cik": _text(root, "issuer/issuerCik"),
        "name": _text(root, "issuer/issuerName"),
    }

    owners = []
    for ro in root.findall("reportingOwner"):
        rel = ro.find("reportingOwnerRelationship")
        owners.append(
            {
                "cik": _text(ro, "reportingOwnerId/rptOwnerCik"),
                "name": _text(ro, "reportingOwnerId/rptOwnerName"),
                "is_director": _flag(rel, "isDirector"),
                "is_officer": _flag(rel, "isOfficer"),
                "is_ten_percent_owner": _flag(rel, "isTenPercentOwner"),
                "officer_title": _text(rel, "officerTitle"),
            }
        )

    net_shares = 0.0
    last_date: str | None = None
    for table_name in ("nonDerivativeTable", "derivativeTable"):
        table = root.find(table_name)
        if table is None:
            continue
        for tx in list(table):
            if not tx.tag.endswith("Transaction"):
                continue
            shares = _text(tx, "transactionAmounts/transactionShares/value")
            adc = _text(tx, "transactionAmounts/transactionAcquiredDisposedCode/value")
            date = _text(tx, "transactionDate/value")
            if shares:
                try:
                    s = float(shares)
                except ValueError:
                    s = 0.0
                if adc == "A":
                    net_shares += s
                elif adc == "D":
                    net_shares -= s
            if date and (last_date is None or date > last_date):
                last_date = date

    return {
        "issuer": issuer,
        "owners": owners,
        "net_shares": net_shares,
        "last_transaction_date": last_date,
        "period_of_report": _text(root, "periodOfReport"),
    }
