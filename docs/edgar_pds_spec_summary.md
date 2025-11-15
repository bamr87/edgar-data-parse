# EDGAR Public Dissemination Service (PDS) Specification Summary

## Overview
The EDGAR Public Dissemination Service (PDS) is a system provided by the U.S. Securities and Exchange Commission (SEC) to disseminate public filings in real-time. The PDS Specification (as detailed in `pds_dissemination_spec.pdf`) outlines the technical requirements, protocols, and formats for accessing disseminated EDGAR filings. This service is crucial for applications needing timely access to submissions like 10-Ks, 10-Qs, and 8-Ks.

Key purposes:
- Enable third-party vendors and users to receive real-time notifications and data feeds of EDGAR filings.
- Support structured data formats (e.g., XBRL) for automated parsing.
- Ensure compliance with SEC dissemination rules, including authentication and rate limits.

## Key Specifications from the PDF

### 1. **System Architecture**
   - **PDS Components**: Includes dissemination servers, subscription models, and data feeds.
   - **Access Methods**: Real-time push (e.g., via WebSocket or FTP) and pull mechanisms (e.g., API queries).
   - **Data Formats**: Filings are disseminated in ZIP archives containing HTML, XML (XBRL), and TXT files.

### 2. **Authentication and Security**
   - Requires user authentication via API keys or certificates.
   - Secure connections (HTTPS/TLS) mandatory.
   - Rate limiting: Similar to EDGAR APIs (e.g., 10 requests/second per IP).

### 3. **Data Feed Details**
   - **Filing Types**: Covers all EDGAR forms (e.g., submissions, amendments).
   - **Metadata**: Includes CIK, accession number, filing date, form type.
   - **XBRL Support**: Disseminated filings include inline XBRL for financial data extraction.
   - **Error Handling**: Specs for retry logic, error codes (e.g., 404 for missing filings).

### 4. **Integration Guidelines**
   - Subscribers must handle large volumes of data with efficient parsing.
   - Compliance with SEC's fair access rules (no redistribution without permission).
   - Testing: Use EDGAR's test environment for development.

For full details, refer to the original `pds_dissemination_spec.pdf` in this directory.

## Incorporation into This Repository

This repo focuses on parsing EDGAR data via public APIs. To incorporate PDS specs for real-time capabilities:

### 1. **Enhance Fetch Module (`src/fetch.py`)**
   - Add PDS-specific functions: E.g., subscribe to real-time feeds using WebSocket libraries (e.g., `websocket-client`).
   - Example: Implement a `subscribe_to_pds_feed()` function that authenticates and streams filings, respecting rate limits with `tenacity` retries.
   - Handle ZIP extraction and XBRL parsing inline with existing `get_facts()` logic.

### 2. **Update Parsing Module (`src/parse.py`)**
   - Extend `facts_DF()` to process PDS-disseminated XBRL directly (e.g., using `xml.etree.ElementTree` for XML parsing).
   - Add real-time parsing: Trigger AI summaries on new filings arrival.

### 3. **AI Integration (`src/ai_summarize.py`)**
   - Use PDS for timely data: E.g., agent prompts like "Summarize the latest 8-K filing for urgent financial analysis."
   - Ensure summaries comply with PDS usage rules (e.g., no unauthorized redistribution).

### 4. **Main App and CLI (`src/main.py`)**
   - Add CLI flags: `--real-time` to enable PDS streaming.
   - Example: `python src/main.py --ticker AAPL --real-time --summarize`

### 5. **Compliance Notes**
   - Update `README.md` with PDS-specific setup (e.g., obtaining SEC credentials).
   - Add logging for PDS interactions to monitor compliance.
   - Dependencies: Add `websocket-client` and `xmltodict` to `requirements.txt` for PDS handling.

By integrating PDS, this app evolves from batch parsing to a real-time EDGAR monitoring tool, enhancing its utility for financial analysis and industry reviews. Future work: Implement full PDS subscription logic.
