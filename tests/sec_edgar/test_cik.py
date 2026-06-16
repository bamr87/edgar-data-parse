"""Tests for canonical CIK normalization."""

import pytest

from sec_edgar.cik import is_valid_cik, normalize_cik


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (320193, "0000320193"),
        ("320193", "0000320193"),
        ("0000320193", "0000320193"),
        ("CIK0000320193", "0000320193"),
        ("  320193 ", "0000320193"),
        ("cik320193", "0000320193"),
        ("0000000001", "0000000001"),
        (1, "0000000001"),
        ("1234567890", "1234567890"),  # full width, no padding
    ],
)
def test_normalize_cik_valid(value, expected):
    assert normalize_cik(value) == expected


@pytest.mark.parametrize("value", ["", "   ", "abc", "CIK", "12345678901", 12345678901])
def test_normalize_cik_invalid(value):
    with pytest.raises(ValueError):
        normalize_cik(value)


def test_is_valid_cik():
    assert is_valid_cik("320193") is True
    assert is_valid_cik(320193) is True
    assert is_valid_cik("") is False
    assert is_valid_cik("not-a-cik") is False
    assert is_valid_cik("123456789012") is False
