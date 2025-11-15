# Comprehensive API Documentation for SEC EDGAR Database

## Introduction

The U.S. Securities and Exchange Commission (SEC) provides public access to the Electronic Data Gathering, Analysis, and Retrieval (EDGAR) system through a set of RESTful APIs hosted at `data.sec.gov`. These APIs allow developers to retrieve company submission histories and eXtensible Business Reporting Language (XBRL) financial data in JSON format. The APIs are designed for programmatic access to EDGAR filings, enabling applications such as financial analysis tools, research platforms, and data aggregators.

Key features:
- **Real-time Updates**: Data is updated as filings are disseminated, with delays typically under one second for submissions and under one minute for XBRL data.
- **No Authentication Required**: APIs are openly accessible without API keys.
- **JSON Responses**: All endpoints return data in JSON format.
- **Bulk Downloads**: ZIP files for large-scale data access, updated nightly.

This documentation expands on the official SEC resources, providing detailed endpoint descriptions, parameters, response structures, examples, and best practices. It addresses gaps in the official explanations by including code samples, error handling details, and structured schemas derived from actual API responses.

**Base URL**: `https://data.sec.gov`

**Official Reference**: For the foundational overview, refer to the SEC's EDGAR APIs page.

## Rate Limits and Best Practices

To ensure fair access, the SEC enforces rate limits on EDGAR APIs and websites:
- **Maximum Request Rate**: 10 requests per second per user. This limit applies across all machines used by the same user or company, identified by IP address or User-Agent header.
- **Download Speed**: Informal observations suggest limits around 30 MB/s, but this is not officially documented.
- **Consequences of Exceeding Limits**: Access may be temporarily restricted or blocked. If rate-limited, the API may return HTTP 429 (Too Many Requests).

**Best Practices**:
- Include a custom User-Agent header in requests, formatted as `CompanyName contact@email.com`, to identify your application and facilitate contact if issues arise.
- Implement exponential backoff for retries on errors like 429.
- Cache responses locally to minimize repeated requests.
- For large datasets, prefer bulk ZIP downloads over individual API calls.
- Comply with SEC's Privacy and Security Policy; avoid scraping if APIs suffice.
- Efficient Scripting: Download only necessary data; for example, fetch specific filings rather than entire histories.

## Authentication

No authentication is required. APIs are public and do not use API keys, tokens, or credentials.

## Error Handling

Responses use standard HTTP status codes. Common errors include:
- **200 OK**: Successful response.
- **400 Bad Request**: Invalid parameters (e.g., malformed CIK).
- **404 Not Found**: Resource not available (e.g., invalid CIK or tag).
- **429 Too Many Requests**: Rate limit exceeded; retry after a delay.
- **500 Internal Server Error**: Rare server-side issues; retry later.

Error responses may include a JSON body with details, e.g., `{"error": "Invalid CIK"}`. Always check the status code and parse the body for messages.

## Endpoints

### 1. Submissions API

**Description**: Retrieves the filing history for a specific entity, including metadata (e.g., company name, tickers, addresses) and a list of recent filings (up to 1,000 or one year, whichever is larger). Additional historical filings are referenced in separate JSON files.

**Endpoint**: `/submissions/CIK{10-digit-cik}.json`

**Method**: GET

**Parameters**:
- `CIK{10-digit-cik}` (required, string): 10-digit Central Index Key, padded with leading zeros (e.g., `0000320193` for Apple Inc.).

**Response Format**: JSON object with company metadata and filings.
- **Root Keys**:
  - `cik` (string): CIK identifier.
  - `entityType` (string): e.g., "operating".
  - `sic` (string): Standard Industrial Classification code.
  - `sicDescription` (string): Description of SIC.
  - `name` (string): Company name.
  - `tickers` (array of strings): Stock tickers.
  - `exchanges` (array of strings): Exchanges.
  - `ein` (string): Employer ID Number.
  - `addresses` (object): Mailing and business addresses (each with `street1`, `city`, `stateOrCountry`, etc.).
  - `phone` (string): Contact phone.
  - `formerNames` (array of objects): Previous names with `name`, `from`, `to`.
  - `filings` (object):
    - `recent` (object): Parallel arrays for recent filings (e.g., `accessionNumber`, `filingDate`, `form`, `size`, `isXBRL`, `primaryDocument`).
    - `files` (array of objects): References to additional JSON files (e.g., `{ "name": "CIK...-submissions-001.json", "filingCount": 1154, "filingFrom": "1994-01-26", "filingTo": "..." }`).
- Derived from example response for CIK0000320193.

**Example Request**:
```
GET https://data.sec.gov/submissions/CIK0000320193.json
User-Agent: YourCompany your@email.com
```

**Example Response Snippet**:
```json
{
  "cik": "0000320193",
  "entityType": "operating",
  "sic": "3571",
  "sicDescription": "Electronic Computers",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "ein": "942404110",
  "addresses": {
    "mailing": {
      "street1": "ONE APPLE PARK WAY",
      "city": "CUPERTINO",
      "stateOrCountry": "CA",
      "zipCode": "95014"
    },
    "business": { ... }
  },
  "phone": "(408) 996-1010",
  "formerNames": [ ... ],
  "filings": {
    "recent": {
      "accessionNumber": ["0000320193-24-000069", ...],
      "filingDate": ["2024-05-03", ...],
      "form": ["10-Q", ...],
      "size": [5304776, ...],
      "isXBRL": [1, ...],
      "primaryDocument": ["aapl-20240330.htm", ...]
    },
    "files": [ ... ]
  }
}
```

**Bulk Download**: Full submissions data in ZIP format.
- URL: `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip`
- Updated: Nightly at ~3:00 a.m. ET.

**Code Example (Python)**:
```python
import requests

headers = {'User-Agent': 'YourCompany your@email.com'}
response = requests.get('https://data.sec.gov/submissions/CIK0000320193.json', headers=headers)
if response.status_code == 200:
    data = response.json()
    print(data['name'])  # Output: Apple Inc.
else:
    print(f"Error: {response.status_code}")
```

### 2. XBRL Company Concept API

**Description**: Returns all XBRL disclosures for a single company and a specific concept (taxonomy/tag), organized by units (e.g., USD). Facts are from non-custom taxonomies and apply to the entire entity.

**Endpoint**: `/api/xbrl/companyconcept/CIK{10-digit-cik}/{taxonomy}/{tag}.json`

**Method**: GET

**Parameters**:
- `CIK{10-digit-cik}` (required, string): As above.
- `{taxonomy}` (required, string): e.g., `us-gaap`, `ifrs-full`, `dei`, `srt`.
- `{tag}` (required, string): XBRL tag, e.g., `AccountsPayableCurrent`.

**Response Format**: JSON object with concept metadata and facts.
- **Root Keys**:
  - `cik` (integer): Numeric CIK.
  - `taxonomy` (string): Taxonomy used.
  - `tag` (string): Concept tag.
  - `label` (string): Human-readable label.
  - `description` (string): Detailed explanation.
  - `entityName` (string): Company name.
  - `units` (object): e.g., `{ "USD": [array of facts] }`.
    - Each fact: `{ "end": "YYYY-MM-DD", "val": number, "accn": string, "fy": integer, "fp": string, "form": string, "filed": "YYYY-MM-DD", "frame": string (optional) }`.
- Derived from example response.

**Example Request**:
```
GET https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/AccountsPayableCurrent.json
User-Agent: YourCompany your@email.com
```

**Example Response Snippet**:
```json
{
  "cik": 320193,
  "taxonomy": "us-gaap",
  "tag": "AccountsPayableCurrent",
  "label": "Accounts Payable, Current",
  "description": "Carrying value as of the balance sheet date of liabilities incurred... (truncated)",
  "entityName": "Apple Inc.",
  "units": {
    "USD": [
      {
        "end": "2008-09-27",
        "val": 5520000000,
        "accn": "0001193125-09-214859",
        "fy": 2009,
        "fp": "FY",
        "form": "10-K",
        "filed": "2009-10-27"
      },
      // Additional facts...
    ]
  }
}
```

**Bulk Download**: Not specific; use Company Facts bulk for related data.

**Code Example (Python)**:
```python
import requests

headers = {'User-Agent': 'YourCompany your@email.com'}
url = 'https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/AccountsPayableCurrent.json'
response = requests.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    print(data['label'])  # Output: Accounts Payable, Current
```

### 3. XBRL Company Facts API

**Description**: Aggregates all XBRL facts for a company across concepts, from non-custom taxonomies, for consistent comparison.

**Endpoint**: `/api/xbrl/companyfacts/CIK{10-digit-cik}.json`

**Method**: GET

**Parameters**:
- `CIK{10-digit-cik}` (required, string): As above.

**Response Format**: JSON object with all concepts.
- **Root Keys**:
  - `cik` (string): CIK.
  - `entityName` (string): Company name.
  - `facts` (object): Nested by taxonomy (e.g., `us-gaap`), then concepts (e.g., `Assets`).
    - Each concept: `{ "label": string, "description": string, "units": { "USD": [facts], ... } }`.
    - Each fact: `{ "start": "YYYY-MM-DD" (optional), "end": "YYYY-MM-DD", "val": number, "accn": string, "fy": integer/null, "fp": string/null, "form": string, "filed": "YYYY-MM-DD", "frame": string (optional) }`.
- Derived from example response.

**Example Request**:
```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
User-Agent: YourCompany your@email.com
```

**Example Response Snippet**:
```json
{
  "cik": "320193",
  "entityName": "Apple Inc.",
  "facts": {
    "us-gaap": {
      "Assets": {
        "label": "Assets",
        "description": "Sum of the carrying amounts as of the balance sheet date of all assets...",
        "units": {
          "USD": [
            {
              "end": "2014-09-27",
              "val": 23353000000,
              "accn": "0001193125-14-383437",
              "fy": 2014,
              "fp": "FY",
              "form": "10-K",
              "filed": "2014-10-27"
            },
            // Additional facts...
          ]
        }
      },
      // Additional concepts...
    }
  }
}
```

**Bulk Download**: Full company facts ZIP.
- URL: `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip`
- Updated: Nightly at ~3:00 a.m. ET.

**Code Example (Python)**:
```python
import requests

headers = {'User-Agent': 'YourCompany your@email.com'}
url = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json'
response = requests.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    print(data['facts']['us-gaap']['NetIncomeLoss']['label'])  # Output: Net Income (Loss)
```

### 4. XBRL Frames API

**Description**: Aggregates the latest fact for each reporting entity fitting a specified calendrical period (annual, quarterly, or instantaneous). Supports non-custom taxonomies.

**Endpoint**: `/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json`

**Method**: GET

**Parameters**:
- `{taxonomy}` (required, string): e.g., `us-gaap`.
- `{tag}` (required, string): e.g., `AccountsPayableCurrent`.
- `{unit}` (required, string): e.g., `USD`, `shares`, `pure`.
- `{period}` (required, string): Calendrical period, e.g., `CY2023` (year), `CY2023Q4` (quarter), `CY2023Q4I` (instantaneous).

**Response Format**: JSON object with aggregated facts across entities.
- **Root Keys**:
  - `taxonomy` (string).
  - `tag` (string).
  - `ccp` (string): Period (e.g., `CY2019Q1I`).
  - `uom` (string): Unit.
  - `label` (string).
  - `description` (string).
  - `pts` (integer): Number of points (facts).
  - `data` (array of objects): Each: `{ "accn": string, "cik": integer/string, "entityName": string, "loc": string (e.g., "US-IL"), "end": "YYYY-MM-DD", "val": number }`.
- Derived from example response.

**Example Request**:
```
GET https://data.sec.gov/api/xbrl/frames/us-gaap/AccountsPayableCurrent/USD/CY2019Q1I.json
User-Agent: YourCompany your@email.com
```

**Example Response Snippet**:
```json
{
  "taxonomy": "us-gaap",
  "tag": "AccountsPayableCurrent",
  "ccp": "CY2019Q1I",
  "uom": "USD",
  "label": "Accounts Payable, Current",
  "description": "Carrying value as of the balance sheet date of liabilities incurred... (truncated)",
  "pts": 3390,
  "data": [
    {
      "accn": "0001104659-19-016320",
      "cik": 1750,
      "entityName": "AAR CORP.",
      "loc": "US-IL",
      "end": "2019-02-28",
      "val": 218600000
    },
    // Additional entities...
  ]
}
```

**Bulk Download**: Not specific; use related XBRL ZIPs for bulk access.

**Code Example (Python)**:
```python
import requests

headers = {'User-Agent': 'YourCompany your@email.com'}
url = 'https://data.sec.gov/api/xbrl/frames/us-gaap/AccountsPayableCurrent/USD/CY2019Q1I.json'
response = requests.get(url, headers=headers)
if response.status_code == 200:
    data = response.json()
    print(data['pts'])  # Output: Number of aggregated facts
```

## Additional Resources

- **Developer FAQs**: For compliance and usage tips.
- **Bulk Data**: Explore daily index files at `https://www.sec.gov/Archives/edgar/daily-index/`.
- **Libraries**: Community tools like `sec-edgar-downloader` (Python) or `edgar` (R) can simplify interactions.

This documentation is based on official SEC sources and example responses as of August 19, 2025. For updates, check the SEC website.