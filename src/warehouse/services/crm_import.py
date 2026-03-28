"""Load CRM JSON rows into CrmCompanyRecord."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from django.db import transaction

from warehouse.models import CrmCompanyRecord

logger = logging.getLogger(__name__)

# Keys we store in dedicated columns; the rest go to ``extra``.
_MAPPED_KEYS = frozenset(
    {
        "Internal Object ID",
        "Key",
        "Name",
        "End User Number",
        "Area",
        "Country",
        "City",
        "Customer Class",
        "Customer Type",
        "Created",
        "Updated",
        "Global HQ Name",
        "Parent Code",
        "Contract Name",
        "Contract Status",
        "Vertical",
        "Display",
        "Import Label",
        "Unique Name",
        "Site Type",
        "Account Id",
        "Language",
        "Has Contract",
    }
)


def _parse_dt(val: Any) -> datetime | None:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _as_bool(val: Any) -> bool | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def iter_crm_objects(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of objects")
    for item in data:
        if isinstance(item, dict):
            yield item


def row_to_crm_fields(row: dict[str, Any]) -> dict[str, Any]:
    extra = {k: v for k, v in row.items() if k not in _MAPPED_KEYS}
    key = str(row.get("Key") or "").strip()
    if not key:
        raise ValueError("Row missing Key")
    ioid = row.get("Internal Object ID")
    try:
        internal_id = int(ioid) if ioid is not None else None
    except (TypeError, ValueError):
        internal_id = None
    return {
        "key": key[:64],
        "internal_object_id": internal_id,
        "name": str(row.get("Name") or "")[:512] or key,
        "end_user_number": (str(row["End User Number"]).strip()[:32] if row.get("End User Number") else None),
        "area": (str(row["Area"])[:64] if row.get("Area") else None),
        "country": (str(row["Country"])[:64] if row.get("Country") else None),
        "city": (str(row["City"])[:255] if row.get("City") else None),
        "customer_class": (str(row["Customer Class"])[:64] if row.get("Customer Class") else None),
        "customer_type": (str(row["Customer Type"])[:64] if row.get("Customer Type") else None),
        "global_hq_name": (str(row["Global HQ Name"])[:512] if row.get("Global HQ Name") else None),
        "parent_code": (str(row["Parent Code"])[:128] if row.get("Parent Code") else None),
        "contract_name": (str(row["Contract Name"])[:512] if row.get("Contract Name") else None),
        "contract_status": (str(row["Contract Status"])[:128] if row.get("Contract Status") else None),
        "vertical": (str(row["Vertical"])[:128] if row.get("Vertical") else None),
        "display": (str(row["Display"])[:512] if row.get("Display") else None),
        "import_label": (str(row["Import Label"])[:128] if row.get("Import Label") else None),
        "unique_name": (str(row["Unique Name"])[:512] if row.get("Unique Name") else None),
        "site_type": (str(row["Site Type"])[:64] if row.get("Site Type") else None),
        "account_id": (str(row["Account Id"])[:64] if row.get("Account Id") else None),
        "language": (str(row["Language"])[:16] if row.get("Language") else None),
        "created_source": _parse_dt(row.get("Created")),
        "updated_source": _parse_dt(row.get("Updated")),
        "has_contract": _as_bool(row.get("Has Contract")),
        "extra": extra,
    }


@transaction.atomic
def load_crm_json_path(path: Path, *, clear_existing: bool = False) -> dict[str, int]:
    if clear_existing:
        n_del, _ = CrmCompanyRecord.objects.all().delete()
        logger.info("Cleared %s CRM rows", n_del)

    inserted = 0
    updated = 0
    errors = 0
    for row in iter_crm_objects(path):
        try:
            fields = row_to_crm_fields(row)
        except ValueError:
            errors += 1
            continue
        _, created = CrmCompanyRecord.objects.update_or_create(
            key=fields["key"],
            defaults={k: v for k, v in fields.items() if k != "key"},
        )
        if created:
            inserted += 1
        else:
            updated += 1
    return {"inserted": inserted, "updated": updated, "errors": errors}
