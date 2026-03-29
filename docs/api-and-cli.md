# API and CLI

All paths below are relative to the API host (e.g. `http://127.0.0.1:8000`). Authenticated vs anonymous behavior follows DRF defaults in settings; many endpoints are open for local development.

## REST API

**Versioned base:** `/api/v1/`  
**Legacy alias:** `/api/` (same routes).

### Health and reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health/` | Liveness. |
| GET | `/api/v1/health/ready/` | Readiness; checks database connectivity. |
| GET | `/api/v1/reference/sic-codes/` | SIC lookup/autocomplete (`q`, `code`, `limit`). |

### Router resources

Registered with `DefaultRouter` (list/create/detail patterns apply where the viewset allows writes):

| Prefix | ViewSet | Notes |
|--------|---------|--------|
| `/companies/` | `CompanyViewSet` | Filter: `ticker`, `cik`, `industry`, `sic_code`, `hq_state`. Search on name/ticker/cik. |
| `/company-metadata/` | `CompanyMetadataViewSet` | Read-only, paginated metadata + filters for dashboards. |
| `/filings/` | `FilingViewSet` | Filing CRUD + custom actions below. |
| `/facts/` | `FactViewSet` | XBRL facts; supports filtering via `FactFilterSet`. |
| `/sections/`, `/tables/` | Section/table CRUD | Linked to filings. |
| `/derived-metrics/` | Read-only | Computed metrics. |
| `/peer-groups/` | `PeerGroupViewSet` | Peer sets + analytics action. |
| `/public-series/` | Read-only | External series catalog. |
| `/public-observations/` | Read-only | Series observations. |
| `/series-bundles/` | `SeriesBundleViewSet` | Bundles by `slug`; nested observations action. |

### Custom actions (`companies`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/companies/edgar-search/?q=&limit=&force_refresh=` | Search `ListedIssuer` directory; optional refresh from SEC. |
| POST | `/api/v1/companies/from-edgar/` | Body: `ticker`, `cik`, optional `name` — get or create `Company`. |
| POST | `/api/v1/companies/bulk-from-edgar-tickers/` | Bulk insert/update from SEC ticker file. |
| POST | `/api/v1/companies/{id}/suggest-schema/` | Heuristic JSON schema hints (placeholder for richer filing-driven logic). |
| POST | `/api/v1/companies/{id}/sync-submissions/` | Sync filing index from SEC. |
| POST | `/api/v1/companies/{id}/sync-facts/` | Sync companyfacts into `Fact`. |
| GET | `/api/v1/companies/{id}/edgar-sync-status/` | Last sync timestamps and error snippet. |
| GET | `/api/v1/companies/{id}/analytics/latest-by-concepts/?concepts=&taxonomy=` | Latest fact per concept. |
| GET | `/api/v1/companies/{id}/analytics/timeseries/?concept=&taxonomy=&limit=` | Time series for one concept. |

### Other custom actions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/company-metadata/facets/` | Aggregates: SIC, state, industry, coverage counts. |
| POST | `/api/v1/filings/ingest-htm/` | Body: `url`, and `ticker` or `cik` — ingest one HTM filing. |
| GET | `/api/v1/facts/facets/?company=` | Per-company fact aggregates (taxonomy, top concepts, years). |
| GET | `/api/v1/peer-groups/{id}/analytics/peer-fact-compare/?concept=&taxonomy=` | Compare concept across peer group. |
| GET | `/api/v1/series-bundles/{slug}/observations/?limit=` | Bundle observations snapshot. |

Interactive exploration: open `/api/v1/` in a browser with Django staff session if browsable API is enabled.

**OpenAPI:** Not configured. This document is the route inventory.

---

## Management commands

Run from `src/` with `PYTHONPATH=src` and `DJANGO_SETTINGS_MODULE=config.settings` (or `cd src` after `pip install`):

```bash
cd src
python manage.py <command> [options]
```

### `sec_edgar`

| Command | Purpose |
|---------|---------|
| `ingest_htm` | Ingest one HTM filing (`--url`, optional `--ticker` / `--cik`). |
| `sync_submissions` | Pull SEC submissions index into `Filing` for a company (`--ticker` / `--cik`). |
| `sync_company_facts` | Load companyfacts into `Fact` (`--ticker` / `--cik`). |
| `sync_listed_issuers` | Refresh `ListedIssuer` from `company_tickers.json`. |
| `bulk_load_edgar_companies` | Upsert `Company` rows from SEC ticker JSON. |
| `bulk_load_edgar_zip` | Load nightly `submissions.zip` / `companyfacts.zip` (heavy). |
| `sync_sic_reference` | Fetch/cache SIC reference JSON under data dir. |
| `sync_accounting_reference` | Merge `data/reference/sources/accounting/` (`acct_facts.csv` + `acct_facts_overlay.json`) into `generated/us_gaap_account_map.json`. |
| `generate_edgar_reference` | Regenerate portions of `data/reference/` from live SEC samples. |

### `warehouse`

| Command | Purpose |
|---------|---------|
| `populate_edgar_database` | Opinionated bootstrap: migrate, listed issuers, optional bulk ZIP, references. |
| `load_crm_companies_json` | Load CRM JSON into `CrmCompanyRecord`. |
| `match_crm_sec_titles` | Match CRM names to SEC issuers. |
| `sync_crm_matched_edgar` | Sync submissions/facts for matched CRM rows (rate-limit friendly). |

### `public_data`

| Command | Purpose |
|---------|---------|
| `load_series_bundle` | Register a bundle JSON (default macro bundle). |
| `sync_series_bundle` | Pull observations for a named bundle (FRED needs `FRED_API_KEY`). |

Use `python manage.py help <command>` for full arguments.
