# Data directory

## `reference/` (stable, app-backed)

JSON bundles checked into git and loaded at runtime (see `sec_edgar.reference_data` and `data/manifest.json`):

| File | Role |
|------|------|
| `edgar_api_schema.json` | Shapes of SEC company facts, submissions, and how API fields map to `warehouse.Fact`. |
| `taxonomies.json` | Common XBRL taxonomy namespaces (`us-gaap`, `dei`, etc.). |
| `financial_model.json` | US-GAAP concept groups (tag preference order) and derived KPI definitions. |
| `accounting_model.json` | Schema notes for the accounting / presentation map and how `data/acct_facts*` sources merge. |
| `generated/us_gaap_account_map.json` | **Generated** — one row per `us-gaap` concept key: label, description, optional `acct_category`. Built from `acct_facts.csv` → `acct_facts.json` → `acct_facts_updated.json` (later wins). |

### Accounting map (acct_facts*)

Source files under `data/`:

- `acct_facts.csv` — compact seed list  
- `acct_facts.json` — extended concepts  
- `acct_facts_updated.json` — same with `acct_category` where present  

Merge into the canonical reference file (used by `sec_edgar.reference_data.load_accounting_by_concept`):

```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=config.settings python src/manage.py sync_accounting_reference
```

If `generated/us_gaap_account_map.json` is missing, the loader falls back to `acct_facts_updated.json`, then `acct_facts.json`, then `acct_facts.csv`.

### Regenerating from EDGAR

From the repo root (with `DJANGO_SETTINGS_MODULE=config.settings`, `PYTHONPATH=src`, and `USER_AGENT_EMAIL` set per SEC policy):

```bash
python src/manage.py generate_edgar_reference
```

This calls SEC **companyfacts** (per `--cik` / `--ticker`, default AAPL + MSFT), **submissions** (for root-key observation), and **companyconcept** for each tag in `financial_model.json`’s `concept_groups`. It rewrites the three JSON files under `reference/`, keeps hand-authored schema text and KPI definitions, and fills `meta.generated_from_edgar` plus `concept_catalog` labels/descriptions.

Add **`--with-accounting`** to run **`sync_accounting_reference`** afterward (merge `acct_facts*` into `generated/us_gaap_account_map.json`).

## Root-level CSV / JSON

Operational or sample exports (CRM companies, ticker lists, account-to-tag lookups). These are not loaded automatically unless you run a specific command or script.

**Company exports:** `companies-sample.csv` is the small tracked example. Full `companies.csv`, `companies.json`, and `companies-clean.json` are typically large and listed in the repo root `.gitignore`; place them under `data/` locally when needed (for example `load_crm_companies_json` defaults to `data/companies-clean.json`).
