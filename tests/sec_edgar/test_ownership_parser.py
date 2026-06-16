"""SEC Form 3/4/5 ownership parser."""

from __future__ import annotations

import pytest

from sec_edgar.parsers.ownership import parse_ownership

FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer><issuerCik>0001318605</issuerCik><issuerName>Tesla, Inc.</issuerName></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerCik>0001494730</rptOwnerCik><rptOwnerName>Musk Elon</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>1</isDirector><isOfficer>1</isOfficer><isTenPercentOwner>1</isTenPercentOwner>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-01-02</value></transactionDate>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-01-05</value></transactionDate>
      <transactionAmounts>
        <transactionShares><value>300</value></transactionShares>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def test_parse_ownership():
    parsed = parse_ownership(FORM4)
    assert parsed["issuer"]["cik"] == "0001318605"
    assert len(parsed["owners"]) == 1
    o = parsed["owners"][0]
    assert o["name"] == "Musk Elon"
    assert o["cik"] == "0001494730"
    assert o["is_director"] and o["is_officer"] and o["is_ten_percent_owner"]
    assert o["officer_title"] == "Chief Executive Officer"
    # net = -1000 (disposed) + 300 (acquired) = -700
    assert parsed["net_shares"] == -700.0
    assert parsed["last_transaction_date"] == "2024-01-05"


def test_parse_ownership_not_a_form():
    with pytest.raises(ValueError):
        parse_ownership("<html><body>not an ownership doc</body></html>")
