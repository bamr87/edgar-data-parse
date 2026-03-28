"""Read SEC User-Agent contact email from API clients (e.g. Vite app)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.request import Request


def sec_user_agent_email_from_request(request: Request) -> str | None:
    raw = request.headers.get("X-Sec-User-Agent-Email", "").strip()
    if raw and "@" in raw and len(raw) <= 254:
        return raw
    return None
