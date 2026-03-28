from pathlib import Path

import pytest

from sec_edgar.parsers.htm import parse_sec_htm


@pytest.fixture
def sample_htm(tmp_path: Path) -> Path:
    p = tmp_path / "t.htm"
    p.write_text(
        """
        <html><body>
        <p><b>Item 1.</b> Business</p>
        <p>We make things.</p>
        <table><tr><td>A</td><td>B</td></tr></table>
        </body></html>
        """,
        encoding="utf-8",
    )
    return p


def test_parse_sec_htm_tables(sample_htm: Path):
    out = parse_sec_htm(sample_htm)
    assert "tables" in out
    assert len(out["tables"]) >= 1
    assert out["tables"][0][0] == ["A", "B"]
