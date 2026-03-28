from __future__ import annotations

from unittest.mock import patch

import pytest
import requests
import responses

from sec_edgar.client import SecEdgarClient, default_headers


def test_default_headers_include_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_AGENT_EMAIL", "test@example.com")
    h = default_headers()
    assert "User-Agent" in h
    assert "test@example.com" in h["User-Agent"]


def test_default_headers_override_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_AGENT_EMAIL", "env@example.com")
    h = default_headers(user_agent_email="override@example.com")
    assert "override@example.com" in h["User-Agent"]
    assert "env@example.com" not in h["User-Agent"]


@responses.activate
def test_company_concept_url_and_parse() -> None:
    url = "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json"
    responses.add(
        responses.GET,
        url,
        json={
            "cik": 320193,
            "taxonomy": "us-gaap",
            "tag": "Revenues",
            "label": "Revenues",
            "description": "Sum of revenue",
            "entityName": "Apple Inc.",
            "units": {"USD": []},
        },
        status=200,
    )
    client = SecEdgarClient()
    data = client.company_concept("320193", "us-gaap", "Revenues")
    assert data["tag"] == "Revenues"
    assert data["label"] == "Revenues"


@responses.activate
def test_get_json_success() -> None:
    url = "https://data.sec.gov/submissions/CIK0000320193.json"
    responses.add(responses.GET, url, json={"cik": "320193", "filings": {}}, status=200)
    client = SecEdgarClient()
    data = client.get_json(url)
    assert data["cik"] == "320193"
    assert len(responses.calls) == 1
    assert "User-Agent" in responses.calls[0].request.headers


@responses.activate
@patch("time.sleep")
def test_get_json_retries_after_429(_mock_sleep: object) -> None:
    url = "https://data.sec.gov/submissions/CIK0000320193.json"
    responses.add(responses.GET, url, status=429)
    responses.add(responses.GET, url, json={"ok": True}, status=200)
    client = SecEdgarClient()
    data = client.get_json(url)
    assert data["ok"] is True
    assert len(responses.calls) == 2


def test_custom_session_injected() -> None:
    session = requests.Session()
    client = SecEdgarClient(session=session)
    assert client.session is session
