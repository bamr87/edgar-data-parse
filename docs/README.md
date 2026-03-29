# Documentation index

Start with the [root README](../README.md) for environment setup, Docker, and tests. Use this folder for deeper technical and product context.

## Architecture and API

- **[architecture.md](architecture.md)** — Django apps, data flow from SEC to the warehouse, DB-first JSON caching. For backend developers and operators.
- **[api-and-cli.md](api-and-cli.md)** — REST base paths, main resources and custom actions, and all Django management commands with short examples. For integrators and maintainers.

## SEC reference (external behavior)

Material that describes SEC systems and APIs (not specific to this repo’s code layout):

- **[sec-reference/edgar-api.md](sec-reference/edgar-api.md)** — `data.sec.gov` endpoints and response shapes, plus alignment with the SEC [Webmaster FAQ — Developers](https://www.sec.gov/about/webmaster-frequently-asked-questions#developers) (User-Agent, 10 req/s fair access, support boundaries, lag, RSS, ticker files).
- **[sec-reference/edgar_pds_spec_summary.md](sec-reference/edgar_pds_spec_summary.md)** — Summary of the EDGAR Public Dissemination Service context.
- **[sec-reference/sec-edgar-database-2024-04-13.md](sec-reference/sec-edgar-database-2024-04-13.md)** — Snapshot notes on the SEC EDGAR database (dated reference).

## Product

- **[../PRD.md](../PRD.md)** — Product requirements and vision. The banner at the top clarifies how much of it is implemented in this repository versus aspirational.

## Data and reference JSON

- **[../data/README.md](../data/README.md)** — Files under `data/reference/`, accounting map sources, and commands that regenerate or sync reference data.

## Contributing and containers

- **[../CONTRIBUTING.md](../CONTRIBUTING.md)** — Local dev, tests, lint, and CI-style checks.
- **[../docker/README.md](../docker/README.md)** — Scripts used by Docker and Compose (entrypoint, CI container).

OpenAPI / Swagger is not enabled in this project; use the DRF browsable API at `/api/v1/` when logged in as staff, or see [api-and-cli.md](api-and-cli.md) for route lists.
