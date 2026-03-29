# EDGAR Analyzer — frontend

React 19 + TypeScript + Vite UI for the Django API in the repo root.

## Scripts

```bash
npm install
npm run dev      # dev server (default http://127.0.0.1:5173)
npm run build    # production bundle to dist/
npm run preview  # serve dist locally
npm run lint     # ESLint
```

## API and proxy

- **Local dev:** Vite proxies `/api` to the backend (default `http://127.0.0.1:8000`). Start Django from `src/` (`python manage.py runserver`) first.
- **`VITE_API_BASE`:** Set in `.env` or `.env.local` to prefix all API URLs (e.g. `https://api.example.com`). Omit trailing slash. When unset, requests use same-origin paths like `/api/v1/...` (works with the proxy or nginx same-origin deploy).
- **SEC `User-Agent`:** The backend must send a contact email to SEC. The UI can supply it per browser via `localStorage` or `VITE_SEC_USER_AGENT_EMAIL`; see [`src/api.ts`](src/api.ts) (`X-Sec-User-Agent-Email` header).

Copy [`frontend/.env.example`](.env.example) if you need a template.

## App routes

| Path | Screen |
|------|--------|
| `/` | Dashboard (`EdgarDashboard`) — health, facets, EDGAR search, sync shortcuts |
| `/explore` | Company metadata table (`CompanyMetadataExplorer`) |
| `/companies/:id` | Single company EDGAR summary (`CompanyEdgarSummary`) |
| `/metadata` | Redirects to `/explore` |

## Layout

- [`src/App.tsx`](src/App.tsx) — router and nav
- [`src/api.ts`](src/api.ts) — typed fetch helpers for `/api/v1/`
- [`src/EdgarDashboard.tsx`](src/EdgarDashboard.tsx), [`CompanyMetadataExplorer.tsx`](src/CompanyMetadataExplorer.tsx), [`CompanyEdgarSummary.tsx`](src/CompanyEdgarSummary.tsx) — main views

Project-wide docs: [../docs/README.md](../docs/README.md), [../README.md](../README.md).
