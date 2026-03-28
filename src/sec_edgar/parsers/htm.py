"""Parse SEC HTM filings into sections and tables."""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

# Typical 10-K/10-Q item headings
_ITEM_HEADING = re.compile(r"^Item\s+\d+[A-Za-z]?\.", re.I)


def parse_sec_htm(file_path: str | Path) -> dict:
    path = Path(file_path)
    html_content = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html_content, "lxml")
    sections: dict[str, str] = {}
    for tag in soup.find_all(["font", "span", "div", "p", "b", "strong", "td"]):
        text = tag.get_text(strip=True)
        if not text or not _ITEM_HEADING.match(text):
            continue
        section_name = text[:200]
        sections[section_name] = ""
        parent = tag.parent
        if parent:
            buf: list[str] = []
            sib = tag.next_sibling
            while sib:
                if getattr(sib, "name", None):
                    st = sib.get_text(separator=" ", strip=True) if hasattr(sib, "get_text") else ""
                    if st and _ITEM_HEADING.match(st):
                        break
                    if sib.name not in ("script", "style") and st:
                        buf.append(st)
                sib = getattr(sib, "next_sibling", None)
            if buf:
                sections[section_name] = "\n".join(buf)

    tables: list[list[list[str]]] = []
    for table in soup.find_all("table"):
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = [
                td.get_text(separator=" ", strip=True)
                for td in tr.find_all(["td", "th"])
                if td.get_text(strip=True)
            ]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)

    return {"sections": sections, "tables": tables}
