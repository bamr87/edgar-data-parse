"""DRF permission classes for the EDGAR API."""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Allow read-only access to anyone; writes require an authenticated staff user.

    This is the project-wide default (see ``REST_FRAMEWORK`` in settings). It gates
    every unsafe method — including the SEC-hitting POST ``@action`` endpoints
    (sync, ingest, bulk, resolve, compute) — behind ``is_staff`` while keeping all
    GET/HEAD/OPTIONS reads public.
    """

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
