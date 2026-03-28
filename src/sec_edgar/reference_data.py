"""Load static EDGAR schema and financial model JSON from data/reference/.

Refresh merged content from SEC with ``manage.py generate_edgar_reference`` (see ``data/README.md``).
After replacing files in a long-lived process, call ``clear_reference_cache()`` if you need fresh JSON.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings


def reference_root() -> Path:
    return Path(settings.BASE_DIR).parent / "data" / "reference"


@lru_cache(maxsize=16)
def load_reference_json(filename: str) -> dict[str, Any]:
    path = reference_root() / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def concept_group_frozensets() -> dict[str, frozenset[str]]:
    data = load_reference_json("financial_model.json")
    raw = data.get("concept_groups") or {}
    return {str(k): frozenset(v) for k, v in raw.items() if isinstance(v, list)}


@lru_cache(maxsize=1)
def load_accounting_by_concept() -> dict[str, dict[str, Any]]:
    from sec_edgar.services.accounting_reference import load_accounting_by_concept_resolved

    return load_accounting_by_concept_resolved()


def clear_reference_cache() -> None:
    load_reference_json.cache_clear()
    concept_group_frozensets.cache_clear()
    load_accounting_by_concept.cache_clear()
