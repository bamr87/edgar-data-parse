import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getCompany,
  getEdgarSyncStatus,
  getFilingsForCompany,
  getLatestByConcepts,
  getResolvedSecUserAgentEmail,
  syncCompanyFacts,
  syncCompanySubmissions,
  type AnalyticsLatestValue,
  type CompanyRecord,
  type EdgarSyncStatusResponse,
  type FilingRecord,
} from './api'
import TablePager from './components/TablePager'

/** Latest `us-gaap` facts to show when synced (tune to your pipeline). */
const DEFAULT_KPI_CONCEPTS = [
  'Revenues',
  'Assets',
  'Liabilities',
  'StockholdersEquity',
] as const

type FilingSortField = 'filing_date' | 'form_type' | 'accession_number'

function formatNum(v: number | null | undefined, unit: string | null | undefined): string {
  if (v == null) return '—'
  const u = (unit || '').toLowerCase()
  if (u === 'usd' || u.includes('usd') || u === 'shares') {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(v)
  }
  return String(v)
}

function formatTs(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
  } catch {
    return iso
  }
}

async function loadSyncAndKpis(id: number): Promise<{
  sync: EdgarSyncStatusResponse | null
  kpis: Record<string, AnalyticsLatestValue>
}> {
  const [syncStatus, latest] = await Promise.all([
    getEdgarSyncStatus(id).catch(() => null),
    getLatestByConcepts(id, [...DEFAULT_KPI_CONCEPTS]).catch(() => ({
      company: id,
      taxonomy: 'us-gaap',
      values: {} as Record<string, AnalyticsLatestValue>,
    })),
  ])
  return {
    sync: syncStatus,
    kpis: latest.values || {},
  }
}

export default function CompanyEdgarSummary() {
  const { id: idParam } = useParams<{ id: string }>()
  const [company, setCompany] = useState<CompanyRecord | null>(null)
  const [sync, setSync] = useState<EdgarSyncStatusResponse | null>(null)
  const [filings, setFilings] = useState<FilingRecord[]>([])
  const [filingsCount, setFilingsCount] = useState(0)
  const [filingsLoading, setFilingsLoading] = useState(false)
  const [filingsErr, setFilingsErr] = useState<string | null>(null)
  const [filingsPage, setFilingsPage] = useState(1)
  const [filingsPageSize, setFilingsPageSize] = useState(25)
  const [filingsOrdering, setFilingsOrdering] = useState('-filing_date')
  const [filingsSearch, setFilingsSearch] = useState('')
  const [debouncedFilingsSearch, setDebouncedFilingsSearch] = useState('')
  const [kpis, setKpis] = useState<Record<string, AnalyticsLatestValue>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncingFromSec, setSyncingFromSec] = useState(false)
  const [syncActionErr, setSyncActionErr] = useState<string | null>(null)
  const [syncActionSummary, setSyncActionSummary] = useState<string | null>(null)

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedFilingsSearch(filingsSearch), 350)
    return () => window.clearTimeout(id)
  }, [filingsSearch])

  useEffect(() => {
    setFilingsPage(1)
  }, [debouncedFilingsSearch, filingsPageSize, idParam])

  useEffect(() => {
    const id = Number(idParam)
    if (!Number.isFinite(id) || id < 1) {
      setError('Invalid company id.')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)
    setCompany(null)
    setSync(null)
    setFilings([])
    setFilingsCount(0)
    setFilingsErr(null)
    setKpis({})
    setFilingsSearch('')
    setDebouncedFilingsSearch('')
    setFilingsPage(1)
    setFilingsOrdering('-filing_date')

    void (async () => {
      try {
        const co = await getCompany(id)
        if (cancelled) return
        setCompany(co)

        const slices = await loadSyncAndKpis(id)
        if (cancelled) return
        setSync(slices.sync)
        setKpis(slices.kpis)
      } catch (e) {
        if (cancelled) return
        const msg = e instanceof Error ? e.message : String(e)
        if (msg.startsWith('404')) {
          setError('Company not found.')
        } else {
          setError(msg)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [idParam])

  useEffect(() => {
    const id = Number(idParam)
    if (!Number.isFinite(id) || id < 1 || !company) return

    let cancelled = false
    setFilingsLoading(true)
    setFilingsErr(null)
    void (async () => {
      try {
        const data = await getFilingsForCompany(id, {
          page: filingsPage,
          page_size: filingsPageSize,
          ordering: filingsOrdering,
          search: debouncedFilingsSearch,
        })
        if (cancelled) return
        const rows = Array.isArray(data.results) ? data.results : []
        const n = typeof data.count === 'number' ? data.count : rows.length
        setFilings(rows)
        setFilingsCount(n)
      } catch (e) {
        if (cancelled) return
        setFilingsErr(e instanceof Error ? e.message : String(e))
        setFilings([])
        setFilingsCount(0)
      } finally {
        if (!cancelled) setFilingsLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [
    idParam,
    company,
    filingsPage,
    filingsPageSize,
    filingsOrdering,
    debouncedFilingsSearch,
  ])

  const filingsTotalPages = Math.max(1, Math.ceil(filingsCount / filingsPageSize) || 1)

  useEffect(() => {
    if (filingsCount === 0) return
    const maxPage = Math.max(1, Math.ceil(filingsCount / filingsPageSize))
    if (filingsPage > maxPage) setFilingsPage(maxPage)
  }, [filingsCount, filingsPageSize, filingsPage])

  const toggleFilingSort = (field: FilingSortField) => {
    setFilingsPage(1)
    setFilingsOrdering((o) => {
      if (o === field) return `-${field}`
      if (o === `-${field}`) return field
      return `-${field}`
    })
  }

  const filingSortIndicator = (field: FilingSortField) => {
    if (filingsOrdering === field) return ' ▲'
    if (filingsOrdering === `-${field}`) return ' ▼'
    return ''
  }

  const runPopulateFromSec = async () => {
    const id = Number(idParam)
    if (!Number.isFinite(id) || id < 1) return
    setSyncActionErr(null)
    setSyncActionSummary(null)
    setSyncingFromSec(true)
    try {
      const sub = await syncCompanySubmissions(id)
      const facts = await syncCompanyFacts(id)
      const slices = await loadSyncAndKpis(id)
      setSync(slices.sync)
      setKpis(slices.kpis)
      const filingsData = await getFilingsForCompany(id, {
        page: filingsPage,
        page_size: filingsPageSize,
        ordering: filingsOrdering,
        search: debouncedFilingsSearch,
      })
      const rows = Array.isArray(filingsData.results) ? filingsData.results : []
      const n = typeof filingsData.count === 'number' ? filingsData.count : rows.length
      setFilings(rows)
      setFilingsCount(n)
      setSyncActionSummary(
        `Loaded ${sub.filings_processed} filing row(s) and ${facts.facts_loaded} fact row(s).`,
      )
    } catch (e) {
      setSyncActionErr(e instanceof Error ? e.message : String(e))
    } finally {
      setSyncingFromSec(false)
    }
  }

  const cikDigits = company?.cik?.replace(/^0+/, '') || company?.cik || ''
  const secBrowseUrl = company
    ? `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${encodeURIComponent(cikDigits)}&owner=exclude&count=40`
    : ''

  return (
    <div className="app meta-app detail-app">
      <a className="skip-link" href="#detail-main">
        Skip to main content
      </a>
      <header className="header meta-header detail-header">
        <nav className="detail-breadcrumb" aria-label="Breadcrumb">
          <Link className="nav-link" to="/">
            Dashboard
          </Link>
          <span className="detail-bc-sep" aria-hidden>
            /
          </span>
          <Link className="nav-link" to="/explore">
            Companies
          </Link>
        </nav>
        {loading && <h1>Loading…</h1>}
        {!loading && company && <h1>{company.name}</h1>}
        {!loading && !company && error && <h1>Company</h1>}
        {!loading && company && (
          <p className="tagline">
            {company.ticker && (
              <>
                <strong>{company.ticker}</strong>
                {' · '}
              </>
            )}
            CIK {company.cik}
            {secBrowseUrl && (
              <>
                {' · '}
                <a href={secBrowseUrl} target="_blank" rel="noreferrer">
                  SEC EDGAR
                </a>
              </>
            )}
          </p>
        )}
      </header>

      <main id="detail-main" className="detail-layout">
        {error && <p className="error">{error}</p>}

        {!loading && company && (
          <>
            <section className="panel detail-panel" aria-labelledby="detail-sync-h">
              <h2 id="detail-sync-h">EDGAR sync</h2>
              <p className="dash-hint">
                Pull the SEC submissions index and company facts JSON for this CIK. Requires a
                contact email for SEC requests — set it on the{' '}
                <Link className="nav-link" to="/">
                  dashboard
                </Link>{' '}
                (or <code>VITE_SEC_USER_AGENT_EMAIL</code>) so the API can send{' '}
                <code>X-Sec-User-Agent-Email</code>.
              </p>
              {!getResolvedSecUserAgentEmail() && (
                <p className="error detail-sync-warn" role="status">
                  No SEC contact email configured; the API may reject requests to data.sec.gov.
                </p>
              )}
              <div className="detail-sync-actions">
                <button
                  type="button"
                  className="button"
                  disabled={syncingFromSec}
                  onClick={() => void runPopulateFromSec()}
                >
                  {syncingFromSec ? 'Fetching from SEC…' : 'Load submissions & facts from SEC'}
                </button>
              </div>
              {syncActionErr && <p className="error">{syncActionErr}</p>}
              {syncActionSummary && !syncActionErr && (
                <p className="muted detail-sync-summary" role="status">
                  {syncActionSummary}
                </p>
              )}
              {sync ? (
                <dl className="detail-dl">
                  <div>
                    <dt>Submissions synced</dt>
                    <dd>{formatTs(sync.submissions_synced_at)}</dd>
                  </div>
                  <div>
                    <dt>Facts synced</dt>
                    <dd>{formatTs(sync.facts_synced_at)}</dd>
                  </div>
                  {sync.last_error ? (
                    <div className="detail-sync-err">
                      <dt>Last error</dt>
                      <dd>{sync.last_error}</dd>
                    </div>
                  ) : null}
                </dl>
              ) : (
                <p className="muted">Sync status unavailable.</p>
              )}
            </section>

            <section className="panel detail-panel" aria-labelledby="detail-kpi-h">
              <h2 id="detail-kpi-h">Key facts (latest period)</h2>
              <p className="dash-hint">US GAAP concepts when facts have been synced into the warehouse.</p>
              <div className="detail-kpi-grid">
                {DEFAULT_KPI_CONCEPTS.map((concept) => {
                  const row = kpis[concept]
                  return (
                    <div key={concept} className="detail-kpi-card">
                      <span className="detail-kpi-label">{concept}</span>
                      <span className="detail-kpi-value">
                        {row
                          ? formatNum(row.value, row.unit)
                          : '—'}
                      </span>
                      {row?.period_end && (
                        <span className="detail-kpi-period">Period end {row.period_end}</span>
                      )}
                    </div>
                  )
                })}
              </div>
              {Object.keys(kpis).length === 0 && (
                <p className="muted">No matching facts yet. Sync company facts from the API or CLI.</p>
              )}
            </section>

            <section className="panel detail-panel" aria-labelledby="detail-filings-h">
              <h2 id="detail-filings-h">Recent filings</h2>
              <div className="table-toolbar">
                <label className="meta-field table-toolbar-search">
                  <span className="meta-field-label">Filter</span>
                  <input
                    className="input"
                    type="search"
                    placeholder="Form type or accession…"
                    value={filingsSearch}
                    onChange={(e) => setFilingsSearch(e.target.value)}
                    autoComplete="off"
                    aria-label="Filter filings by form or accession"
                  />
                </label>
              </div>
              {filingsErr && <p className="error">{filingsErr}</p>}
              {filingsLoading && (
                <p className="muted" role="status">
                  Loading filings…
                </p>
              )}
              {!filingsLoading &&
                filingsCount === 0 &&
                filings.length === 0 &&
                !filingsErr && (
                <p className="muted">
                  {debouncedFilingsSearch.trim()
                    ? 'No filings match this filter.'
                    : 'No filings stored for this company yet.'}
                </p>
              )}
              {!filingsLoading && (filingsCount > 0 || filings.length > 0) && (
                <>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th scope="col">
                            <button
                              type="button"
                              className="th-sort"
                              onClick={() => toggleFilingSort('form_type')}
                            >
                              Form{filingSortIndicator('form_type')}
                            </button>
                          </th>
                          <th scope="col">
                            <button
                              type="button"
                              className="th-sort"
                              onClick={() => toggleFilingSort('filing_date')}
                            >
                              Filing date{filingSortIndicator('filing_date')}
                            </button>
                          </th>
                          <th scope="col">
                            <button
                              type="button"
                              className="th-sort"
                              onClick={() => toggleFilingSort('accession_number')}
                            >
                              Accession{filingSortIndicator('accession_number')}
                            </button>
                          </th>
                          <th scope="col">Link</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filings.map((f) => (
                          <tr key={f.id}>
                            <td>{f.form_type}</td>
                            <td>{f.filing_date || '—'}</td>
                            <td className="detail-mono">{f.accession_number}</td>
                            <td>
                              {f.url ? (
                                <a href={f.url} target="_blank" rel="noreferrer">
                                  View
                                </a>
                              ) : (
                                '—'
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <TablePager
                    page={filingsPage}
                    totalPages={filingsTotalPages}
                    totalCount={filingsCount}
                    onPageChange={setFilingsPage}
                    pageSize={filingsPageSize}
                    pageSizeOptions={[10, 25, 50, 100]}
                    onPageSizeChange={(n) => {
                      setFilingsPageSize(n)
                      setFilingsPage(1)
                    }}
                    disabled={filingsLoading}
                  />
                </>
              )}
            </section>

            <section className="panel detail-panel" aria-labelledby="detail-meta-h">
              <h2 id="detail-meta-h">Profile</h2>
              <dl className="detail-dl">
                <div>
                  <dt>Industry</dt>
                  <dd>{company.industry || '—'}</dd>
                </div>
                <div>
                  <dt>SIC</dt>
                  <dd>
                    {company.sic_code || '—'}
                    {company.sic_description ? ` — ${company.sic_description}` : ''}
                  </dd>
                </div>
                <div>
                  <dt>Headquarters</dt>
                  <dd>
                    {[company.hq_city, company.hq_state, company.hq_country]
                      .filter(Boolean)
                      .join(', ') || company.headquarters || '—'}
                  </dd>
                </div>
              </dl>
            </section>
          </>
        )}
      </main>
    </div>
  )
}
