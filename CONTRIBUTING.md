# Contributing

## Prerequisites

- Python 3.12+
- Node.js 20+ (for the Vite frontend)
- Optional: Docker with Compose (matches CI-style checks)

## Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp src/.env.example src/.env
# Set USER_AGENT_EMAIL for any command that calls SEC.
```

Run Django from `src/`:

```bash
cd src
python manage.py migrate
python manage.py runserver
```

`PYTHONPATH` and `DJANGO_SETTINGS_MODULE` are set automatically when using `cd src` and the project layout; tests use `config.settings_test` via `pytest.ini` / `pyproject.toml`.

## Lint and tests

From the repository root:

```bash
ruff check src tests
ruff format src tests
pytest -q
```

Coverage thresholds apply in Docker CI (`docker compose --profile ci`); local `pytest` runs without the coverage gate unless you pass the same flags as [`docker/ci.sh`](docker/ci.sh).

## Frontend

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## Migrations

After model changes:

```bash
cd src
python manage.py makemigrations
python manage.py makemigrations --check --dry-run   # CI-style
```

## Documentation

- Index: [`docs/README.md`](docs/README.md)
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- API and CLI inventory: [`docs/api-and-cli.md`](docs/api-and-cli.md)

## SEC usage

Identify your application with a valid contact in `User-Agent` (`USER_AGENT_EMAIL` / `SEC_USER_AGENT_EMAIL` per settings). Follow [SEC fair access](https://www.sec.gov/os/webmaster-faq#code-support) guidance.
