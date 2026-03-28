"""Django settings for pytest and CI (imported via DJANGO_SETTINGS_MODULE)."""

# Import production-like settings, then tighten for tests.
from .settings import *  # noqa: F403

DEBUG = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests must not call SEC/FRED unless explicitly mocked; keys may still be set in env.
ALLOWED_HOSTS = ["*"]
