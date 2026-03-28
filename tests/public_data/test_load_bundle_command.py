from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.management import call_command

from public_data.models import SeriesBundle


@pytest.mark.django_db
def test_load_series_bundle_from_file(tmp_path: Path) -> None:
    p = tmp_path / "bundle.json"
    p.write_text(
        json.dumps(
            {
                "slug": "pytest-bundle",
                "name": "Pytest Bundle",
                "description": "",
                "series": [{"provider": "fred", "id": "ABC123", "note": "test"}],
            }
        ),
        encoding="utf-8",
    )
    call_command("load_series_bundle", file=str(p))
    b = SeriesBundle.objects.get(slug="pytest-bundle")
    assert b.items.count() == 1
