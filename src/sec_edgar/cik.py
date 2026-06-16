"""Canonical CIK normalization.

SEC Central Index Keys are up to 10 digits and are zero-padded to width 10 in
``data.sec.gov`` URLs (e.g. ``CIK0000320193``). Inputs arrive as ints, bare
strings, already-padded strings, or messy values (``"CIK0000320193"``,
``"320193 "``). Route all of them through :func:`normalize_cik` so the rest of
the codebase deals in one canonical form.
"""

from __future__ import annotations

import re

CIK_WIDTH = 10
_NON_DIGITS = re.compile(r"\D")


def normalize_cik(value: str | int) -> str:
    """Return the 10-digit zero-padded CIK string for ``value``.

    Strips any non-digit characters (handles ``"CIK0000320193"``, whitespace,
    ints). Raises :class:`ValueError` if no digits are present or the CIK has
    more than 10 significant digits.
    """
    digits = _NON_DIGITS.sub("", str(value))
    if not digits:
        raise ValueError(f"No CIK digits found in {value!r}")
    if len(digits.lstrip("0")) > CIK_WIDTH:
        raise ValueError(f"CIK has more than {CIK_WIDTH} digits: {value!r}")
    return digits.zfill(CIK_WIDTH)


def is_valid_cik(value: str | int) -> bool:
    """True if :func:`normalize_cik` would succeed for ``value``."""
    try:
        normalize_cik(value)
    except ValueError:
        return False
    return True
