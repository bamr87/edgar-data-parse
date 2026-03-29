import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getCompany,
  getConceptTimeseries,
  getEdgarSyncStatus,
  getFilingsForCompany,
  getLatestByConcepts,
  getResolvedSecUserAgentEmail,
  syncCompanyFacts,
  syncCompanySubmissions,
  type AnalyticsLatestValue,
  type CompanyRecord,
  type ConceptTimeseriesPoint,
  type EdgarSyncStatusResponse,
  type FilingRecord,
} from './api'
import TablePager from './components/TablePager'

/** Latest `us-gaap` facts to show when synced (tune to your pipeline). */
const DEFAULT_KPI_CONCEPTS = [
  'Revenues',
  'OperatingIncomeLoss',
  'NetIncomeLoss',
  'CashAndCashEquivalentsAtCarryingValue',
  'Assets',
  'Liabilities',
  'StockholdersEquity',
] as const

const KPI_DISPLAY_LABELS: Record<(typeof DEFAULT_KPI_CONCEPTS)[number], string> = {
  Revenues: 'Revenue',
  OperatingIncomeLoss: 'Operating income',
  NetIncomeLoss: 'Net income',
  CashAndCashEquivalentsAtCarryingValue: 'Cash & equivalents',
  Assets: 'Total assets',
  Liabilities: 'Total liabilities',
  StockholdersEquity: "Stockholders' equity",
}

const FILING_QUICK_FILTERS = [
  { label: '10-K', value: '10-K' },
  { label: '10-Q', value: '10-Q' },
  { label: '8-K', value: '8-K' },
  { label: 'DEF 14A', value: 'DEF 14A' },
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

/** Human-readable unit for labels (skill: state currency / measure explicitly). */
function formatMeasureLabel(unit: string | null | undefined): string {
  if (!unit) return ''
  const u = unit.toLowerCase()
  if (u === 'usd' || u.includes('usd')) return 'USD'
  if (u === 'shares') return 'shares'
  if (u === 'pure' || u === 'number') return ''
  return unit
}

function periodRange(row: AnalyticsLatestValue): string | null {
  const a = row.period_end
  const b = row.period_start
  if (a && b && a !== b) return `${b} → ${a}`
  if (a) return `Period end ${a}`
  return null
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

/** Analyst context: how old the warehouse facts snapshot is. */
function formatFactsStaleness(iso: string | null | undefined): string | null {
  if (!iso) return null
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return null
  const days = Math.floor((Date.now() - t) / 86_400_000)
  if (days <= 0) return 'Facts sync: same day'
  if (days === 1) return 'Facts sync: 1 day ago'
  return `Facts sync: ${days} days ago`
}

function formatDimensionsShort(dims: Record<string, unknown> | undefined): string | null {
  if (!dims || typeof dims !== 'object') return null
  const keys = Object.keys(dims).filter((k) => dims[k] != null && dims[k] !== '')
  if (!keys.length) return null
  const parts = keys.slice(0, 4).map((k) => `${k}=${String(dims[k])}`)
  const more = keys.length > 4 ? ` (+${keys.length - 4})` : ''
  return parts.join(', ') + more
}

function buildKpiSnapshotTsv(
  company: CompanyRecord,
  taxonomy: string,
  kpis: Record<string, AnalyticsLatestValue>,
): string {
  const header = ['concept', 'label', 'value', 'unit', 'period_start', 'period_end', 'dimensions_json']
  const rows = DEFAULT_KPI_CONCEPTS.map((concept) => {
    const row = kpis[concept]
    const label = KPI_DISPLAY_LABELS[concept]
    const dims =
      row?.dimensions && Object.keys(row.dimensions).length
        ? JSON.stringify(row.dimensions)
        : ''
    return [
      concept,
      label,
      row?.value != null ? String(row.value) : '',
      row?.unit ?? '',
      row?.period_start ?? '',
      row?.period_end ?? '',
      dims,
    ]
  })
  const pre = [
    `# ${company.name} (${company.ticker ?? 'no ticker'}) CIK ${company.cik}`,
    `# taxonomy=${taxonomy} source=warehouse XBRL facts — verify material figures in filed 10-K/10-Q`,
    '',
  ]
  return pre.join('\n') + [header.join('\t'), ...rows.map((r) => r.join('\t'))].join('\n')
}

async function loadSyncAndKpis(id: number): Promise<{
  sync: EdgarSyncStatusResponse | null
  kpis: Record<string, AnalyticsLatestValue>
  taxonomy: string
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
    taxonomy: latest.taxonomy || 'us-gaap',
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
  const [kpiTaxonomy, setKpiTaxonomy] = useState('us-gaap')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncingFromSec, setSyncingFromSec] = useState(false)
  const [syncActionErr, setSyncActionErr] = useState<string | null>(null)
  const [syncActionSummary, setSyncActionSummary] = useState<string | null>(null)

  const [historyConcept, setHistoryConcept] = useState<string>('Revenues')
  const [historySeries, setHistorySeries] = useState<ConceptTimeseriesPoint[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyErr, setHistoryErr] = useState<string | null>(null)
  const [copyKpiStatus, setCopyKpiStatus] = useState<'idle' | 'ok' | 'err'>('idle')

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
    setKpiTaxonomy('us-gaap')
    setHistoryConcept('Revenues')
    setHistorySeries([])
    setHistoryErr(null)
    setCopyKpiStatus('idle')
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
        setKpiTaxonomy(slices.taxonomy)
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

  useEffect(() => {
    const id = Number(idParam)
    if (!Number.isFinite(id) || id < 1 || !company) return
    const c = historyConcept.trim()
    if (!c) return
    let cancelled = false
    setHistoryLoading(true)
    setHistoryErr(null)
    void (async () => {
      try {
        const data = await getConceptTimeseries(id, c, {
          taxonomy: kpiTaxonomy,
          limit: 24,
        })
        if (cancelled) return
        setHistorySeries(Array.isArray(data.series) ? data.series : [])
      } catch (e) {
        if (cancelled) return
        setHistoryErr(e instanceof Error ? e.message : String(e))
        setHistorySeries([])
      } finally {
        if (!cancelled) setHistoryLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [idParam, company, historyConcept, kpiTaxonomy, sync?.facts_synced_at])

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

  const copyKpiSnapshot = async () => {
    if (!company) return
    const text = buildKpiSnapshotTsv(company, kpiTaxonomy, kpis)
    try {
      await navigator.clipboard.writeText(text)
      setCopyKpiStatus('ok')
      window.setTimeout(() => setCopyKpiStatus('idle'), 2500)
    } catch {
      setCopyKpiStatus('err')
      window.setTimeout(() => setCopyKpiStatus('idle'), 4000)
    }
  }

  const applyFilingQuickFilter = (form: string) => {
    setFilingsSearch(form)
    setFilingsPage(1)
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
      setKpiTaxonomy(slices.taxonomy)
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
            <aside className="fa-analyst-strip" role="note">
              <p>
                <strong>How to use this screen:</strong> figures below are{' '}
                <strong>facts from your warehouse</strong> (XBRL-derived when synced)—not
                investment advice. Compare period-over-period and to official 10-K/10-Q filings; treat
                non-GAAP or adjusted metrics separately when you add them to the pipeline.
              </p>
            </aside>

            <section className="panel detail-panel" aria-labelledby="detail-sync-h">
              <h2 id="detail-sync-h">EDGAR sync</h2>
              <p className="dash-hint">
                Pull the SEC submissions index and company facts JSON for this CIK (see{' '}
                <a
                  href="https://www.sec.gov/edgar/sec-api-documentation"
                  target="_blank"
                  rel="noreferrer"
                >
                  SEC API documentation
                </a>
                ). Requires a contact email for SEC requests — set it on the{' '}
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
                    <dd>
                      {formatTs(sync.facts_synced_at)}
                      {formatFactsStaleness(sync.facts_synced_at) ? (
                        <span className="fa-sync-stale"> · {formatFactsStaleness(sync.facts_synced_at)}</span>
                      ) : null}
                    </dd>
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

            <section
              className="panel detail-panel"
              aria-labelledby="detail-kpi-h"
              aria-describedby="detail-kpi-desc"
            >
              <h2 id="detail-kpi-h">Financial highlights (XBRL)</h2>
              <p id="detail-kpi-desc" className="dash-hint fa-kpi-intro">
                Latest period per concept from taxonomy <code>{kpiTaxonomy}</code> stored in the
                warehouse. Values are <strong>not audited in this app</strong>—anchor decisions to
                filed statements and footnotes.
              </p>
              <div className="fa-kpi-toolbar">
                <button
                  type="button"
                  className="button button-secondary fa-kpi-copy"
                  onClick={() => void copyKpiSnapshot()}
                  disabled={!company}
                >
                  Copy TSV (spreadsheet / notes)
                </button>
                {copyKpiStatus === 'ok' ? (
                  <span className="muted small fa-kpi-copy-msg" role="status">
                    Copied with units and periods.
                  </span>
                ) : null}
                {copyKpiStatus === 'err' ? (
                  <span className="error small fa-kpi-copy-msg" role="status">
                    Clipboard unavailable — select and copy manually.
                  </span>
                ) : null}
              </div>
              <div className="detail-kpi-grid">
                {DEFAULT_KPI_CONCEPTS.map((concept) => {
                  const row = kpis[concept]
                  const unitTag = row ? formatMeasureLabel(row.unit) : ''
                  const pr = row ? periodRange(row) : null
                  const dimLine = row ? formatDimensionsShort(row.dimensions) : null
                  return (
                    <div key={concept} className="detail-kpi-card">
                      <span className="detail-kpi-label">{KPI_DISPLAY_LABELS[concept]}</span>
                      <span className="detail-kpi-concept" title="US-GAAP XBRL tag">
                        {concept}
                      </span>
                      <div className="detail-kpi-value-row">
                        <span className="detail-kpi-value">
                          {row ? formatNum(row.value, row.unit) : '—'}
                        </span>
                        {unitTag ? (
                          <span className="detail-kpi-unit-tag" title="Measure / currency">
                            {unitTag}
                          </span>
                        ) : null}
                      </div>
                      {pr ? <span className="detail-kpi-period">{pr}</span> : null}
                      {dimLine ? (
                        <details className="fa-kpi-dims">
                          <summary>Dimensions (context)</summary>
                          <span className="fa-kpi-dims-body">{dimLine}</span>
                        </details>
                      ) : null}
                    </div>
                  )
                })}
              </div>
              {Object.keys(kpis).length === 0 && (
                <p className="muted">
                  No matching facts yet. Use “Load submissions & facts from SEC” above or sync via
                  API/CLI.
                </p>
              )}
            </section>

            <section
              className="panel detail-panel fa-history-panel"
              aria-labelledby="detail-history-h"
            >
              <h2 id="detail-history-h">Period history (trend check)</h2>
              <p className="dash-hint">
                Newest periods first—use for period-over-period sense checks; reconcile to the filing
                for the same period end if numbers drive a decision.
              </p>
              <label className="meta-field fa-history-select">
                <span className="meta-field-label">Concept</span>
                <select
                  className="input"
                  value={historyConcept}
                  onChange={(e) => setHistoryConcept(e.target.value)}
                  aria-label="XBRL concept for history table"
                >
                  {DEFAULT_KPI_CONCEPTS.map((c) => (
                    <option key={c} value={c}>
                      {KPI_DISPLAY_LABELS[c]} ({c})
                    </option>
                  ))}
                </select>
              </label>
              {historyErr && <p className="error">{historyErr}</p>}
              {historyLoading && (
                <p className="muted" role="status">
                  Loading history…
                </p>
              )}
              {!historyLoading && !historyErr && historySeries.length === 0 && (
                <p className="muted">No rows for this concept in the warehouse yet.</p>
              )}
              {!historyLoading && historySeries.length > 0 && (
                <div className="table-wrap fa-history-table-wrap">
                  <table className="data-table fa-history-table">
                    <thead>
                      <tr>
                        <th scope="col">Period end</th>
                        <th scope="col">Period start</th>
                        <th scope="col" className="fa-history-num">
                          Value
                        </th>
                        <th scope="col">Unit</th>
                        <th scope="col">Dimensions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historySeries.map((pt, idx) => (
                        <tr key={`${pt.period_end ?? ''}-${pt.period_start ?? ''}-${idx}`}>
                          <td>{pt.period_end || '—'}</td>
                          <td>{pt.period_start || '—'}</td>
                          <td className="fa-history-num">{formatNum(pt.value, pt.unit)}</td>
                          <td>{formatMeasureLabel(pt.unit) || pt.unit || '—'}</td>
                          <td className="fa-history-dims">
                            {formatDimensionsShort(pt.dimensions) || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <div className="fa-analyst-two-col">
              <section className="panel detail-panel fa-sources" aria-labelledby="detail-sources-h">
                <h2 id="detail-sources-h">Sources</h2>
                <ul className="fa-sources-list">
                  <li>
                    <a href={secBrowseUrl} target="_blank" rel="noreferrer">
                      SEC EDGAR — company filings
                    </a>{' '}
                    (official forms, exhibits, MD&A)
                  </li>
                  <li>
                    <a
                      href="https://www.sec.gov/search-filings/edgar-full-text-search"
                      target="_blank"
                      rel="noreferrer"
                    >
                      SEC full-text search
                    </a>
                  </li>
                  <li>
                    Warehouse data: submissions sync{' '}
                    {sync?.submissions_synced_at ? formatTs(sync.submissions_synced_at) : '—'}, facts
                    sync {sync?.facts_synced_at ? formatTs(sync.facts_synced_at) : '—'}.
                  </li>
                </ul>
              </section>
              <section className="panel detail-panel fa-watch" aria-labelledby="detail-watch-h">
                <h2 id="detail-watch-h">Watch / limits</h2>
                <ul className="fa-watch-list">
                  <li>Stale data if sync timestamps are old—refresh from SEC when needed.</li>
                  <li>Default KPIs are illustrative US-GAAP concepts; not every issuer reports every tag.</li>
                  <li>
                    Period history can show multiple rows for the same period end when dimensions
                    (segments, axes) differ—read dimensions before comparing values.
                  </li>
                  <li>
                    <strong>Not</strong> legal, tax, or personalized investment advice—use filings and
                    professional advisors for decisions.
                  </li>
                </ul>
              </section>
            </div>

            <section className="panel detail-panel" aria-labelledby="detail-filings-h">
              <h2 id="detail-filings-h">Recent filings</h2>
              <div className="table-toolbar fa-filing-toolbar">
                <div className="fa-filing-quick" role="group" aria-label="Quick form filters">
                  {FILING_QUICK_FILTERS.map((f) => (
                    <button
                      key={f.value}
                      type="button"
                      className={
                        filingsSearch.trim() === f.value
                          ? 'fa-chip fa-chip-active'
                          : 'fa-chip'
                      }
                      onClick={() => applyFilingQuickFilter(f.value)}
                    >
                      {f.label}
                    </button>
                  ))}
                  {filingsSearch.trim() ? (
                    <button
                      type="button"
                      className="fa-chip fa-chip-clear"
                      onClick={() => {
                        setFilingsSearch('')
                        setFilingsPage(1)
                      }}
                    >
                      Clear filter
                    </button>
                  ) : null}
                </div>
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
                          <th scope="col">Period of report</th>
                          <th scope="col">Link</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filings.map((f) => (
                          <tr key={f.id}>
                            <td>{f.form_type}</td>
                            <td>{f.filing_date || '—'}</td>
                            <td className="detail-mono">{f.accession_number}</td>
                            <td>{f.period_of_report || '—'}</td>
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

            <p className="fa-disclaimer muted small" role="note">
              Informational use only. Interpretation belongs with you and your advisors; this UI
              surfaces structured data and links to regulators—not recommendations.
            </p>

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
