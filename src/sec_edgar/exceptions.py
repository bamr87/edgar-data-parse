"""Typed exceptions for the SEC EDGAR layer.

These let callers (notably the DRF views in ``api/v1``) map failures to correct
HTTP status codes instead of collapsing everything to 502:

* :class:`EdgarRateLimitError`   -> 429 (SEC fair-access throttle)
* :class:`EdgarResolutionError`  -> 404 (ticker/CIK not found)
* :class:`EdgarUpstreamError`    -> 502 (SEC unreachable / unexpected response)
"""

from __future__ import annotations


class EdgarError(Exception):
    """Base class for all sec_edgar errors."""


class EdgarRateLimitError(EdgarError):
    """SEC returned HTTP 429 (fair-access rate limit). Callers should back off."""


class EdgarResolutionError(EdgarError):
    """A ticker or CIK could not be resolved to an SEC entity."""


class EdgarUpstreamError(EdgarError):
    """SEC upstream was unreachable or returned an unexpected response."""
