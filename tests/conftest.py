import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated client (reads are public; writes should be rejected)."""
    return APIClient()


@pytest.fixture
def admin_client(db) -> APIClient:
    """Client authenticated as a staff user (allowed to perform write/sync actions)."""
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        username="admin-test", password="unused-in-tests", is_staff=True, is_superuser=True
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def fred_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "test-fred-key")
