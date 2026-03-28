"""Load SEC nightly EDGAR bulk ZIPs (companyfacts, submissions) into the warehouse."""

from __future__ import annotations

import json
import logging
import re
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Literal

from sec_edgar.client import SecEdgarClient
from sec_edgar.services.company_facts import sync_company_facts_to_db
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company

logger = logging.getLogger(__name__)

URL_COMPANYFACTS_ZIP = (
    "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
)
URL_SUBMISSIONS_ZIP = (
    "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
)

_CIK_JSON_NAME = re.compile(r"^CIK(\d{10})\.json$", re.IGNORECASE)


def parse_cik_from_zip_member(name: str) -> str | None:
    """Return 10-digit CIK if ``name`` is a ``CIK##########.json`` archive member."""
    base = name.rsplit("/", 1)[-1]
    m = _CIK_JSON_NAME.match(base)
    return m.group(1) if m else None


def _default_name_from_payload(cik: str, payload: dict[str, Any], kind: Literal["facts", "submissions"]) -> str:
    if kind == "facts":
        raw = payload.get("entityName")
    else:
        raw = payload.get("name")
    if raw and str(raw).strip():
        return str(raw).strip()[:255]
    return f"CIK {cik}"


def ensure_company_for_bulk(
    cik: str,
    payload: dict[str, Any],
    *,
    kind: Literal["facts", "submissions"],
    only_existing: bool,
) -> Company | None:
    cik = cik.zfill(10)
    if only_existing:
        return Company.objects.filter(cik=cik).first()
    name = _default_name_from_payload(cik, payload, kind)
    company, _ = Company.objects.get_or_create(
        cik=cik,
        defaults={"name": name},
    )
    return company


def download_bulk_zip(url: str, dest: Path, *, user_agent_email: str | None = None) -> None:
    client = SecEdgarClient(user_agent_email=user_agent_email)
    client.download_binary_to_path(url, dest)


def _sorted_cik_members(zip_path: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(zip_path) as zf:
        out: list[tuple[str, str]] = []
        for name in zf.namelist():
            cik = parse_cik_from_zip_member(name)
            if cik:
                out.append((name, cik))
    out.sort(key=lambda x: x[1])
    return out


def _should_process_cik(
    cik: str,
    *,
    cik_allowlist: set[str] | None,
    start_after_cik: str | None,
) -> bool:
    if cik_allowlist is not None and cik not in cik_allowlist:
        return False
    if start_after_cik and cik <= start_after_cik.zfill(10):
        return False
    return True


def _load_zip_json(zip_path: Path, member: str) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member, "r") as fp:
            return json.load(fp)


def process_companyfacts_zip(
    zip_path: Path,
    *,
    user_agent_email: str | None = None,
    only_existing_companies: bool = False,
    cik_allowlist: set[str] | None = None,
    start_after_cik: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    return _process_zip(
        zip_path,
        kind="facts",
        sync_fn=_sync_facts,
        user_agent_email=user_agent_email,
        only_existing_companies=only_existing_companies,
        cik_allowlist=cik_allowlist,
        start_after_cik=start_after_cik,
        limit=limit,
        dry_run=dry_run,
        delay_seconds=delay_seconds,
    )


def process_submissions_zip(
    zip_path: Path,
    *,
    user_agent_email: str | None = None,
    only_existing_companies: bool = False,
    cik_allowlist: set[str] | None = None,
    start_after_cik: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    return _process_zip(
        zip_path,
        kind="submissions",
        sync_fn=_sync_submissions,
        user_agent_email=user_agent_email,
        only_existing_companies=only_existing_companies,
        cik_allowlist=cik_allowlist,
        start_after_cik=start_after_cik,
        limit=limit,
        dry_run=dry_run,
        delay_seconds=delay_seconds,
    )


def _sync_facts(company: Company, payload: dict[str, Any], *, user_agent_email: str | None) -> int:
    return sync_company_facts_to_db(company, payload, user_agent_email=user_agent_email)


def _sync_submissions(company: Company, payload: dict[str, Any], *, user_agent_email: str | None) -> int:
    return sync_submissions_for_company(company, payload, user_agent_email=user_agent_email)


def _process_zip(
    zip_path: Path,
    *,
    kind: Literal["facts", "submissions"],
    sync_fn: Callable[..., int],
    user_agent_email: str | None = None,
    only_existing_companies: bool = False,
    cik_allowlist: set[str] | None = None,
    start_after_cik: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    members = _sorted_cik_members(zip_path)
    processed = 0
    skipped = 0
    rows_touched = 0
    errors: list[str] = []

    for member, cik in members:
        if not _should_process_cik(
            cik, cik_allowlist=cik_allowlist, start_after_cik=start_after_cik
        ):
            skipped += 1
            continue

        if only_existing_companies and not Company.objects.filter(cik=cik).exists():
            skipped += 1
            continue

        if limit is not None and processed >= limit:
            break

        if dry_run:
            processed += 1
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            continue

        try:
            payload = _load_zip_json(zip_path, member)
        except Exception as e:
            errors.append(f"{cik} read: {e}"[:500])
            continue

        company = ensure_company_for_bulk(
            cik,
            payload,
            kind=kind,
            only_existing=only_existing_companies,
        )
        if company is None:
            skipped += 1
            continue

        try:
            n = sync_fn(company, payload, user_agent_email=user_agent_email)
            rows_touched += n
        except Exception as e:
            logger.exception("Bulk %s failed for CIK %s", kind, cik)
            errors.append(f"{cik}: {e}"[:500])
            continue

        processed += 1
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return {
        "zip": str(zip_path),
        "kind": kind,
        "members_matched": len(members),
        "processed": processed,
        "skipped": skipped,
        "rows_touched": rows_touched,
        "dry_run": dry_run,
        "errors": errors[:50],
        "error_count": len(errors),
    }


def resolve_zip_path(
    *,
    url: str,
    local_path: Path | None,
    cache_dir: Path | None,
    user_agent_email: str | None,
) -> Path:
    """Return path to a ZIP: use ``local_path`` if set, else download to ``cache_dir`` or temp."""
    if local_path is not None:
        p = Path(local_path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        return p

    base = cache_dir or Path(tempfile.gettempdir()) / "edgar_bulk_zips"
    base = Path(base).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    dest = base / url.rsplit("/", 1)[-1]
    download_bulk_zip(url, dest, user_agent_email=user_agent_email)
    return dest


def run_bulk_load(
    *,
    load_submissions: bool,
    load_facts: bool,
    submissions_zip: Path | None,
    facts_zip: Path | None,
    submissions_url: str,
    facts_url: str,
    cache_dir: Path | None,
    user_agent_email: str | None = None,
    only_existing_companies: bool = False,
    cik_allowlist: set[str] | None = None,
    start_after_cik: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    """Resolve paths, optionally download, run submissions first then facts."""
    result: dict[str, Any] = {
        "submissions": None,
        "facts": None,
    }

    if load_submissions:
        path = resolve_zip_path(
            url=submissions_url,
            local_path=submissions_zip,
            cache_dir=cache_dir,
            user_agent_email=user_agent_email,
        )
        result["submissions"] = process_submissions_zip(
            path,
            user_agent_email=user_agent_email,
            only_existing_companies=only_existing_companies,
            cik_allowlist=cik_allowlist,
            start_after_cik=start_after_cik,
            limit=limit,
            dry_run=dry_run,
            delay_seconds=delay_seconds,
        )

    if load_facts:
        path = resolve_zip_path(
            url=facts_url,
            local_path=facts_zip,
            cache_dir=cache_dir,
            user_agent_email=user_agent_email,
        )
        result["facts"] = process_companyfacts_zip(
            path,
            user_agent_email=user_agent_email,
            only_existing_companies=only_existing_companies,
            cik_allowlist=cik_allowlist,
            start_after_cik=start_after_cik,
            limit=limit,
            dry_run=dry_run,
            delay_seconds=delay_seconds,
        )

    return result
