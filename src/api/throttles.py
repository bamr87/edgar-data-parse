"""Custom DRF throttles."""

from __future__ import annotations

from rest_framework.throttling import UserRateThrottle


class SecActionThrottle(UserRateThrottle):
    """Tighter, dedicated limit for SEC-hitting actions (sync/ingest/bulk/resolve).

    Uses the ``sec`` rate from ``REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`` so live
    SEC calls stay within fair-access limits independently of the general user rate.
    """

    scope = "sec"
