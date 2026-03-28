import pytest
from django.test import Client


@pytest.mark.django_db
def test_api_v1_health():
    c = Client()
    r = c.get("/api/v1/health/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
