"""Legacy alias: /api/* mirrors /api/v1/*. Prefer /api/v1/ for new clients."""

from django.urls import include, path

urlpatterns = [
    path("", include("api.v1.urls")),
]
