# EDGAR data parse

Django + Django REST Framework backend with a Vite/React UI for **SEC EDGAR** company data and optional **FRED** macro series.

## Stack

- **Backend**: Python 3.12+, Django 5+, DRF, `sec_edgar` (direct SEC APIs), `public_data` (FRED)
- **Frontend**: React + TypeScript (Vite) in [`frontend/`](frontend/)
- **Database**: SQLite by default; set `DATABASE_URL` for PostgreSQL

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp src/.env.example src/.env   # set USER_AGENT_EMAIL (required by SEC)
cd src
python manage.py migrate
python manage.py runserver
```

API base: **http://127.0.0.1:8000/api/v1/** (legacy **/api/** mirrors the same routes).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Optional: set `VITE_API_BASE` (e.g. production API URL). See [`frontend/README.md`](frontend/README.md).

## Environment

See [`src/.env.example`](src/.env.example). Important:

- **`USER_AGENT_EMAIL`**: SEC requires a descriptive `User-Agent` identifying you.
- **`FRED_API_KEY`**: needed for `sync_series_bundle` / FRED observations.
- **`DJANGO_SECRET_KEY`**: set a strong value when `DJANGO_DEBUG=false`.

## Common tasks

Typical flows (from `src/`):

```bash
cd src
python manage.py ingest_htm --url 'https://www.sec.gov/Archives/edgar/data/.../file.htm' --ticker AAPL
python manage.py sync_submissions --ticker AAPL
python manage.py sync_company_facts --ticker AAPL
python manage.py load_series_bundle
python manage.py sync_series_bundle --slug macro
```

Same sync actions are available on the API, for example `POST /api/v1/companies/{id}/sync-submissions/` and `POST /api/v1/companies/{id}/sync-facts/`. **Full command list, CRM pipeline, and bulk ZIP loaders** are documented in [`docs/api-and-cli.md`](docs/api-and-cli.md).

Bundles are defined in [`src/public_data/bundles/macro.json`](src/public_data/bundles/macro.json). Observations: `GET /api/v1/series-bundles/macro/observations/`.

### Sample company list (reference data, not ingested by Django)

[`data/samples/companies-sample.csv`](data/samples/companies-sample.csv) is a small CRM-style export checked into git. Large exports go under **`data/local/`** (gitignored), e.g. `data/local/companies-clean.json` for `load_crm_companies_json`, or `data/local/erp-clients.csv` → `csv_to_json.py` / `clean_json.py`. Legacy flat paths under `data/*.csv` / `*.json` remain gitignored for older checkouts. SEC issuers live in the `warehouse` app after sync/ingest. If an older database still has table `erp_clients_erpclientrow`, drop it or recreate the DB; Django no longer ships that app.

### CLI (no Django DB)

```bash
python src/main.py --action process_htm --url 'https://www.sec.gov/Archives/.../file.htm'
python src/main.py --ticker AAPL --action fetch    # writes companyfacts JSON under data/
```

## Project layout

- [`src/config/`](src/config/) — Django settings and URLs
- [`src/warehouse/`](src/warehouse/) — `Company`, `Filing`, `Fact`, `DerivedMetric`, peers
- [`src/sec_edgar/`](src/sec_edgar/) — SEC client, HTM parser, ingest + sync services
- [`src/public_data/`](src/public_data/) — external series catalog + FRED sync
- [`src/api/v1/`](src/api/v1/) — versioned REST API
- [`tests/`](tests/) — pytest + pytest-django

Data layout (reference, samples, local): [`data/README.md`](data/README.md).

## Docker Compose

From the repo root, **PostgreSQL + API** (port **8000**), with `./data` mounted for reference JSON and HTM artifacts:

```bash
docker compose up -d --build
curl -s http://127.0.0.1:8000/api/v1/health/
```

Optional env (shell or a `.env` file next to `docker-compose.yml`): `DJANGO_SECRET_KEY`, `USER_AGENT_EMAIL`, `DJANGO_DEBUG`, `CORS_ALLOWED_ORIGINS`. Container entrypoints are summarized in [`docker/README.md`](docker/README.md).

**Vite dev UI** (port **5173**), proxying `/api` to the API container:

```bash
docker compose --profile dev up -d --build
```

For the Compose `frontend` service, `API_PROXY_TARGET=http://web:8000` is set in [`docker-compose.yml`](docker-compose.yml). For Vite on the host, omit it; the default is `http://127.0.0.1:8000` (see [`frontend/.env.example`](frontend/.env.example)).

**Static UI + nginx** (port **8080**), same-origin `/api` proxied to Django:

```bash
docker compose --profile prod up -d --build
```

**CI-style checks in containers** (ruff, `makemigrations --check`, `manage.py check`, pytest against Postgres). Mounts `./data` for reference files used in tests:

```bash
docker compose --profile ci run --rm test
```

Single-image API build (no Compose) still works:

```bash
docker build -t edgar-analyzer .
docker run -p 8000:8000 -e USER_AGENT_EMAIL=you@example.com edgar-analyzer
```

## Tests & CI

```bash
pytest -q
```

GitHub Actions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs Ruff, migration checks, `manage.py check`, pytest (SQLite and PostgreSQL), and `npm ci` + production build for the Vite frontend. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for matching local commands.

## Documentation

- **[`docs/README.md`](docs/README.md)** — Index of all technical and reference docs.
- **[`docs/architecture.md`](docs/architecture.md)** — Apps, data flow, DB-first SEC caching.
- **[`docs/api-and-cli.md`](docs/api-and-cli.md)** — REST routes and `manage.py` commands.
- **[`docs/sec-reference/`](docs/sec-reference/)** — SEC API and PDS context (external behavior).
- **[`PRD.md`](PRD.md)** — Product vision and roadmap (see banner there for scope vs code).
