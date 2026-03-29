import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  edgarCompanySearch,
  companyFromEdgar,
  findCompanyIdByCik,
  getFacets,
  getResolvedSecUserAgentEmail,
  searchCompanyMetadata,
  SEC_USER_AGENT_EMAIL_STORAGE_KEY,
  type CompanyMetadataListResponse,
  type EdgarSearchResult,
  type FacetsResponse,
} from './api'

function pct(part: number, whole: number): string {
  if (!whole) return '0'
  return `${Math.round((100 * part) / whole)}%`
}

export default function EdgarDashboard() {
  const navigate = useNavigate()
  const [facets, setFacets] = useState<FacetsResponse | null>(null)
  const [facetsErr, setFacetsErr] = useState<string | null>(null)

  const [warehouseQ, setWarehouseQ] = useState('')
  const [debouncedWarehouse, setDebouncedWarehouse] = useState('')
  const [warehouseLoading, setWarehouseLoading] = useState(false)
  const [warehouseErr, setWarehouseErr] = useState<string | null>(null)
  const [warehouseHits, setWarehouseHits] = useState<CompanyMetadataListResponse['results']>([])

  const [secQ, setSecQ] = useState('')
  const [debouncedSec, setDebouncedSec] = useState('')
  const [secLoading, setSecLoading] = useState(false)
  const [secErr, setSecErr] = useState<string | null>(null)
  const [secHits, setSecHits] = useState<EdgarSearchResult[]>([])
  const [addingCik, setAddingCik] = useState<string | null>(null)

  const [secEmailDraft, setSecEmailDraft] = useState(() => getResolvedSecUserAgentEmail())

  useEffect(() => {
    void (async () => {
      try {
        const data = await getFacets()
        setFacets(data)
        setFacetsErr(null)
      } catch (e) {
        setFacetsErr(e instanceof Error ? e.message : String(e))
      }
    })()
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedWarehouse(warehouseQ), 350)
    return () => window.clearTimeout(id)
  }, [warehouseQ])

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSec(secQ), 350)
    return () => window.clearTimeout(id)
  }, [secQ])

  useEffect(() => {
    const q = debouncedWarehouse.trim()
    if (!q) {
      setWarehouseHits([])
      setWarehouseErr(null)
      setWarehouseLoading(false)
      return
    }
    let cancelled = false
    setWarehouseLoading(true)
    setWarehouseErr(null)
    void (async () => {
      try {
        const data = await searchCompanyMetadata({ search: q, page_size: 8 })
        if (cancelled) return
        setWarehouseHits(data.results)
      } catch (e) {
        if (cancelled) return
        setWarehouseErr(e instanceof Error ? e.message : String(e))
        setWarehouseHits([])
      } finally {
        if (!cancelled) setWarehouseLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [debouncedWarehouse])

  useEffect(() => {
    const q = debouncedSec.trim()
    if (q.length < 2) {
      setSecHits([])
      setSecErr(null)
      setSecLoading(false)
      return
    }
    let cancelled = false
    setSecLoading(true)
    setSecErr(null)
    void (async () => {
      try {
        const data = await edgarCompanySearch(q, 50)
        if (cancelled) return
        setSecHits(data.results)
      } catch (e) {
        if (cancelled) return
        setSecErr(e instanceof Error ? e.message : String(e))
        setSecHits([])
      } finally {
        if (!cancelled) setSecLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [debouncedSec])

  const openWarehouseCompany = (id: number) => {
    navigate(`/companies/${id}`)
  }

  const openSecMatch = async (row: EdgarSearchResult) => {
    if (row.in_warehouse) {
      const wid = await findCompanyIdByCik(row.cik)
      if (wid != null) {
        navigate(`/companies/${wid}`)
        return
      }
      setSecErr('Marked in warehouse but no company row matched this CIK. Try “Add to warehouse”.')
      return
    }
    setAddingCik(row.cik)
    setSecErr(null)
    try {
      const body =
        row.ticker != null && row.ticker !== ''
          ? { ticker: row.ticker }
          : { cik: row.cik }
      const created = await companyFromEdgar(body)
      navigate(`/companies/${created.id}`)
    } catch (e) {
      setSecErr(e instanceof Error ? e.message : String(e))
    } finally {
      setAddingCik(null)
    }
  }

  const persistSecEmail = () => {
    const v = secEmailDraft.trim()
    try {
      if (v) localStorage.setItem(SEC_USER_AGENT_EMAIL_STORAGE_KEY, v)
      else localStorage.removeItem(SEC_USER_AGENT_EMAIL_STORAGE_KEY)
    } catch {
      /* private mode */
    }
    setSecEmailDraft(getResolvedSecUserAgentEmail())
  }

  return (
    <div className="app meta-app dash-app">
      <a className="skip-link" href="#dash-main">
        Skip to main content
      </a>
      <header className="header meta-header">
        <h1>EDGAR company dashboard</h1>
        <p className="tagline">
          Search the warehouse or SEC&apos;s issuer directory, then open a company for filings, sync
          status, and key facts. For informational use only.
        </p>
        <aside className="fa-dash-context" role="note">
          <p>
            <strong>Two sources:</strong> <em>Warehouse</em> is your loaded Postgres data;{' '}
            <em>SEC directory</em> queries the live issuer list. Financial numbers on company pages
            come from synced XBRL facts—always verify material figures against the filed 10-K/10-Q.
          </p>
        </aside>
        <p className="dash-nav-links">
          <Link className="nav-link" to="/explore">
            Browse all companies
          </Link>
        </p>
      </header>

      <main id="dash-main" className="dash-layout">
        {facetsErr && <p className="error">{facetsErr}</p>}

        {facets && (
          <section className="panel meta-summary" aria-labelledby="dash-summary-heading">
            <h2 id="dash-summary-heading">Warehouse coverage</h2>
            <div className="meta-stat-grid">
              <div className="meta-stat">
                <span className="meta-stat-value">{facets.totals.companies.toLocaleString()}</span>
                <span className="meta-stat-label">Companies</span>
              </div>
              <div className="meta-stat">
                <span className="meta-stat-value">
                  {pct(facets.totals.with_sic_code, facets.totals.companies)}
                </span>
                <span className="meta-stat-label">With SIC code</span>
              </div>
              <div className="meta-stat">
                <span className="meta-stat-value">
                  {pct(facets.totals.with_naics_code, facets.totals.companies)}
                </span>
                <span className="meta-stat-label">With NAICS</span>
              </div>
              <div className="meta-stat">
                <span className="meta-stat-value">
                  {pct(facets.totals.with_industry_text, facets.totals.companies)}
                </span>
                <span className="meta-stat-label">With industry text</span>
              </div>
            </div>
          </section>
        )}

        <div className="dash-search-grid">
          <section className="panel dash-panel" aria-labelledby="dash-wh-heading">
            <h2 id="dash-wh-heading">Warehouse search</h2>
            <p className="dash-hint">Matches name, ticker, CIK, and other metadata fields.</p>
            <label className="meta-field">
              <span className="meta-field-label">Search</span>
              <input
                className="input"
                type="search"
                value={warehouseQ}
                onChange={(e) => setWarehouseQ(e.target.value)}
                placeholder="Company name or ticker…"
                autoComplete="off"
              />
            </label>
            {warehouseErr && <p className="error">{warehouseErr}</p>}
            {warehouseLoading && <p className="muted dash-muted">Searching…</p>}
            {!warehouseLoading &&
              !debouncedWarehouse.trim() &&
              warehouseHits.length === 0 &&
              !warehouseErr && (
                <p className="muted dash-empty-hint">
                  Type a name, ticker, or CIK to search companies already loaded in the warehouse.
                </p>
              )}
            <ul className="dash-hit-list" aria-live="polite">
              {warehouseHits.map((row) => (
                <li key={row.id}>
                  <button
                    type="button"
                    className="dash-hit-button"
                    onClick={() => openWarehouseCompany(row.id)}
                  >
                    <span className="dash-hit-title">{row.name}</span>
                    <span className="dash-hit-meta">
                      {row.ticker || '—'} · {row.cik}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {!warehouseLoading && debouncedWarehouse.trim() && warehouseHits.length === 0 && (
              <p className="muted">No matches.</p>
            )}
          </section>

          <section className="panel dash-panel" aria-labelledby="dash-sec-heading">
            <h2 id="dash-sec-heading">SEC issuer directory</h2>
            <p className="dash-hint">
              Uses SEC&apos;s listed-issuer data. Set a contact email below so the API can identify
              your requests (SEC policy).
            </p>
            <label className="meta-field">
              <span className="meta-field-label">Search (min. 2 characters)</span>
              <input
                className="input"
                type="search"
                value={secQ}
                onChange={(e) => setSecQ(e.target.value)}
                placeholder="Ticker, name, or CIK digits…"
                autoComplete="off"
              />
            </label>
            {secErr && <p className="error">{secErr}</p>}
            {secLoading && <p className="muted dash-muted">Searching…</p>}
            {!secLoading &&
              debouncedSec.trim().length < 2 &&
              secHits.length === 0 &&
              !secErr && (
                <p className="muted dash-empty-hint">
                  Enter at least two characters to search SEC&apos;s listed-issuer directory (ticker,
                  name, or CIK digits).
                </p>
              )}
            <ul className="dash-hit-list" aria-live="polite">
              {secHits.map((row) => (
                <li key={row.cik}>
                  <div className="dash-sec-row">
                    <div className="dash-sec-info">
                      <span className="dash-hit-title">{row.name}</span>
                      <span className="dash-hit-meta">
                        {row.ticker || '—'} · {row.cik}
                        {row.in_warehouse ? (
                          <span className="dash-badge dash-badge-in">In warehouse</span>
                        ) : (
                          <span className="dash-badge dash-badge-out">Not loaded</span>
                        )}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="button button-secondary dash-sec-action"
                      disabled={addingCik === row.cik}
                      onClick={() => void openSecMatch(row)}
                    >
                      {row.in_warehouse
                        ? addingCik === row.cik
                          ? 'Opening…'
                          : 'Open'
                        : addingCik === row.cik
                          ? 'Adding…'
                          : 'Add & open'}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            {!secLoading && debouncedSec.trim().length >= 2 && secHits.length === 0 && (
              <p className="muted">No matches.</p>
            )}
          </section>
        </div>

        <details className="settings-disclosure">
          <summary>SEC request identification</summary>
          <div className="settings-body">
            <p className="muted small">
              Stored in local storage as <code>{SEC_USER_AGENT_EMAIL_STORAGE_KEY}</code> and sent as{' '}
              <code>X-Sec-User-Agent-Email</code>. Falls back to{' '}
              <code>VITE_SEC_USER_AGENT_EMAIL</code> when unset.
            </p>
            <label className="meta-field">
              <span className="meta-field-label">Contact email</span>
              <input
                className="input"
                type="email"
                value={secEmailDraft}
                onChange={(e) => setSecEmailDraft(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </label>
            <button type="button" className="button" onClick={persistSecEmail}>
              Save
            </button>
          </div>
        </details>
      </main>
    </div>
  )
}
