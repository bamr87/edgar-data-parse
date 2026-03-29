# Data directory layout

## `reference/` (stable, app-backed)

JSON loaded at runtime (`sec_edgar.reference_data`, `data/manifest.json`).

| File | Role |
|------|------|
| `edgar_api_schema.json` | SEC company facts / submissions shapes and mapping notes. |
| `taxonomies.json` | XBRL taxonomy namespaces (`us-gaap`, `dei`, …). |
| `financial_model.json` | US-GAAP concept groups (tag preference) and derived KPI definitions. |
| `accounting_model.json` | How accounting sources merge into the canonical map. |
| `sic_codes.json` | SEC SIC master list. |
| `generated/us_gaap_account_map.json` | **Generated** — one entry per `us-gaap` concept: label, description, optional `acct_category`. |

### Accounting sources (`reference/sources/accounting/`)

| File | Role |
|------|------|
| `acct_facts.csv` | Compact seed list (`us_gaap_list`, `acct_label`, `acct_description`). |
| `acct_facts_overlay.json` | JSON array with the full concept set; optional `acct_category`. Loaded **after** the CSV so it **wins** per concept. |

This replaces the older trio `acct_facts.csv` + `acct_facts.json` + `acct_facts_updated.json` (the two JSON files had identical concept keys; only the overlay file is kept).

Merge into the canonical reference file:

```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=config.settings python src/manage.py sync_accounting_reference
```

If `generated/us_gaap_account_map.json` is missing, the loader falls back to `acct_facts_overlay.json`, then `acct_facts.csv`.

### Regenerating reference JSON from EDGAR

From the repo root (`USER_AGENT_EMAIL` set per SEC policy):

```bash
python src/manage.py generate_edgar_reference
```

Add **`--with-accounting`** to run **`sync_accounting_reference`** afterward.

## `samples/` (tracked, small)

Example rows for documentation and local experiments: CRM-style CSV, CRM sync snippet, optional `us_gaap_facts.csv`.

## `local/` (gitignored)

Place large or proprietary exports here (not committed). Examples:

- `companies-clean.json` — default path for `load_crm_companies_json`
- `companies.csv` / `companies.json` — full CRM/ERP exports
- `erp-clients.csv` — input for `src/csv_to_json.py` (writes `local/erp-clients.json`)

The repo root `.gitignore` keeps `data/local/*` ignored except `data/local/.gitkeep`.
