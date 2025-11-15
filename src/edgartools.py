from edgar import core
from edgar import _filings

identity = core.set_identity("amr@bash-365.com")

print(identity)

filings = _filings.get_filings(ticker='VMI')

filing = filings[0]
text = filing.text()