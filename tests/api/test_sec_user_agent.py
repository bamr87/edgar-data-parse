from __future__ import annotations

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from api.sec_user_agent import sec_user_agent_email_from_request


@pytest.mark.parametrize(
    ("header_value", "expected"),
    [
        ("ops@example.com", "ops@example.com"),
        ("", None),
        ("not-an-email", None),
    ],
)
def test_sec_user_agent_email_from_request(header_value: str, expected: str | None) -> None:
    factory = APIRequestFactory()
    django_req = factory.get("/", HTTP_X_SEC_USER_AGENT_EMAIL=header_value)
    req = Request(django_req)
    assert sec_user_agent_email_from_request(req) == expected


def test_sec_user_agent_email_missing_header() -> None:
    req = Request(APIRequestFactory().get("/"))
    assert sec_user_agent_email_from_request(req) is None
