"""SGML submission parser + content extraction (Phase 8)."""

from __future__ import annotations

from sec_edgar.parsers.submission import parse_submission, submission_header_field
from sec_edgar.services.content_extraction import extract_text

SAMPLE = """<SEC-DOCUMENT>0000320193-23-000106.txt : 20231103
<SEC-HEADER>0000320193-23-000106.hdr.sgml : 20231103
ACCESSION NUMBER:		0000320193-23-000106
CONFORMED SUBMISSION TYPE:	10-K
</SEC-HEADER>
<DOCUMENT>
<TYPE>10-K
<SEQUENCE>1
<FILENAME>aapl-20230930.htm
<DESCRIPTION>10-K
<TEXT>
<html><body><p>Apple annual report: revenue growth strong.</p><script>x()</script></body></html>
</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-23.1
<SEQUENCE>2
<FILENAME>aapl-ex231.htm
<DESCRIPTION>EXHIBIT 23.1
<TEXT>
<html><body>Consent of independent registered accounting firm.</body></html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""


def test_parse_submission_yields_documents():
    docs = list(parse_submission(SAMPLE))
    assert len(docs) == 2
    assert docs[0]["type"] == "10-K"
    assert docs[0]["sequence"] == 1
    assert docs[0]["file_name"] == "aapl-20230930.htm"
    assert docs[0]["content_type"] == "text/html"
    assert len(docs[0]["sha1"]) == 40
    assert docs[1]["type"] == "EX-23.1"
    assert docs[1]["sequence"] == 2
    # Distinct content -> distinct hashes.
    assert docs[0]["sha1"] != docs[1]["sha1"]


def test_submission_header_fields():
    assert submission_header_field(SAMPLE, "ACCESSION NUMBER") == "0000320193-23-000106"
    assert submission_header_field(SAMPLE, "CONFORMED SUBMISSION TYPE") == "10-K"


def test_extract_text_strips_html_and_scripts():
    html = "<html><body><p>Hello</p><script>evil()</script><style>x{}</style> world</body></html>"
    text = extract_text(html, "text/html")
    assert "Hello" in text
    assert "world" in text
    assert "evil" not in text


def test_extract_text_plain_passthrough():
    assert extract_text("just text", "text/plain") == "just text"
