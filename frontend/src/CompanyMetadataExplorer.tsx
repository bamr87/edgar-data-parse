import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, fetchSicCodes, type SicReferenceRow } from './api'
import TablePager from './components/TablePager'
import './App.css'

export type CompanyMetadataRow = {
  id: number
  cik: string
  ticker: string | null
  name: string
  industry: string | null
  sic_code: string | null
  sic_description: string | null
  naics_code: string | null
  hq_state: string | null
  hq_country: string
  hq_city: string | null
  headquarters: string | null
  size: string | null
  crm_external_key: string | null
  customer_class: string | null
  customer_type: string | null
  customer_vertical: string | null
  contract_status: string | null
  created_at: string
  updated_at: string
}

type FacetsResponse = {
  totals: {
    companies: number
    with_sic_code: number
    with_naics_code: number
    with_industry_text: number
  }
  top_sic: { sic_code: string; sic_description: string; count: number }[]
  hq_state: { hq_state: string; count: number }[]
  industry: { industry: string; count: number }[]
  hq_country: { hq_country: string; count: number }[]
}

type ListResponse = {
  count: number
  next: string | null
  previous: string | null
  results: CompanyMetadataRow[]
}

function buildListQuery(p: {
  page: number
  pageSize: number
  search: string
  ordering: string
  sic_code: string
  hq_state: string
  hq_country: string
  industryIcontains: string
  sicDescriptionIcontains: string
  naicsIcontains: string
}): string {
  const u = new URLSearchParams()
  u.set('page', String(p.page))
  u.set('page_size', String(p.pageSize))
  if (p.search.trim()) u.set('search', p.search.trim())
  if (p.ordering) u.set('ordering', p.ordering)
  if (p.sic_code.trim()) u.set('sic_code', p.sic_code.trim())
  if (p.hq_state.trim()) u.set('hq_state', p.hq_state.trim().toUpperCase())
  if (p.hq_country.trim()) u.set('hq_country', p.hq_country.trim().toUpperCase())
  if (p.industryIcontains.trim()) u.set('industry__icontains', p.industryIcontains.trim())
  if (p.sicDescriptionIcontains.trim()) {
    u.set('sic_description__icontains', p.sicDescriptionIcontains.trim())
  }
  if (p.naicsIcontains.trim()) u.set('naics_code__icontains', p.naicsIcontains.trim())
  return `?${u.toString()}`
}

function pct(part: number, whole: number): string {
  if (!whole) return '0'
  return `${Math.round((100 * part) / whole)}%`
}

export default function CompanyMetadataExplorer() {
  const [facets, setFacets] = useState<FacetsResponse | null>(null)
  const [facetsErr, setFacetsErr] = useState<string | null>(null)
  const [list, setList] = useState<CompanyMetadataRow[]>([])
  const [listCount, setListCount] = useState(0)
  const [listErr, setListErr] = useState<string | null>(null)
  const [listLoading, setListLoading] = useState(false)

  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [ordering, setOrdering] = useState('name')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [sicCode, setSicCode] = useState('')
  const [hqState, setHqState] = useState('')
  const [hqCountry, setHqCountry] = useState('')
  const [industryIcontains, setIndustryIcontains] = useState('')
  const [sicDescriptionIcontains, setSicDescriptionIcontains] = useState('')
  const [naicsIcontains, setNaicsIcontains] = useState('')

  const [sicSuggest, setSicSuggest] = useState<SicReferenceRow[]>([])
  const [sicPreview, setSicPreview] = useState<string | null>(null)
  const [debouncedSicInput, setDebouncedSicInput] = useState('')

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiGet<FacetsResponse>('/api/v1/company-metadata/facets/')
        setFacets(data)
        setFacetsErr(null)
      } catch (e) {
        setFacetsErr(e instanceof Error ? e.message : String(e))
      }
    })()
  }, [])

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSearch(search), 350)
    return () => window.clearTimeout(id)
  }, [search])

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSicInput(sicCode), 280)
    return () => window.clearTimeout(id)
  }, [sicCode])

  useEffect(() => {
    const q = debouncedSicInput.trim()
    if (!q) {
      setSicSuggest([])
      return
    }
    let cancelled = false
    void (async () => {
      try {
        const data = await fetchSicCodes({ q, limit: 20 })
        if (!cancelled) setSicSuggest(data.results)
      } catch {
        if (!cancelled) setSicSuggest([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [debouncedSicInput])

  useEffect(() => {
    const c = sicCode.trim()
    if (!c || !/^\d+$/.test(c)) {
      setSicPreview(null)
      return
    }
    const id = window.setTimeout(() => {
      void fetchSicCodes({ code: c, limit: 1 })
        .then((data) => {
          const row = data.results[0]
          setSicPreview(row ? `${row.industry_title} — ${row.office}` : null)
        })
        .catch(() => setSicPreview(null))
    }, 320)
    return () => window.clearTimeout(id)
  }, [sicCode])

  const loadList = useCallback(async () => {
    setListLoading(true)
    setListErr(null)
    try {
      const q = buildListQuery({
        page,
        pageSize,
        search: debouncedSearch,
        ordering,
        sic_code: sicCode,
        hq_state: hqState,
        hq_country: hqCountry,
        industryIcontains,
        sicDescriptionIcontains,
        naicsIcontains,
      })
      const data = await apiGet<ListResponse>(`/api/v1/company-metadata/${q}`)
      setList(data.results)
      setListCount(data.count)
    } catch (e) {
      setListErr(e instanceof Error ? e.message : String(e))
    } finally {
      setListLoading(false)
    }
  }, [
    page,
    pageSize,
    debouncedSearch,
    ordering,
    sicCode,
    hqState,
    hqCountry,
    industryIcontains,
    sicDescriptionIcontains,
    naicsIcontains,
  ])

  useEffect(() => {
    void loadList()
  }, [loadList])

  const totalPages = Math.max(1, Math.ceil(listCount / pageSize))

  const toggleSort = (field: string) => {
    setPage(1)
    setOrdering((o) => {
      if (o === field) return `-${field}`
      if (o === `-${field}`) return field
      return field
    })
  }

  const sortIndicator = (field: string) => {
    if (ordering === field) return ' ▲'
    if (ordering === `-${field}`) return ' ▼'
    return ''
  }

  const clearFilters = () => {
    setSearch('')
    setDebouncedSearch('')
    setSicCode('')
    setHqState('')
    setHqCountry('')
    setIndustryIcontains('')
    setSicDescriptionIcontains('')
    setNaicsIcontains('')
    setSicSuggest([])
    setSicPreview(null)
    setOrdering('name')
    setPage(1)
  }

  const maxSicBar = facets?.top_sic.length
    ? Math.max(...facets.top_sic.map((x) => x.count), 1)
    : 1

  return (
    <div className="app meta-app">
      <a className="skip-link" href="#meta-main">
        Skip to main content
      </a>
      <header className="header meta-header">
        <h1>Company metadata</h1>
        <p className="tagline">
          Filter, sort, and scan warehouse companies by industry, SIC, NAICS, headquarters, and
          related fields. Open a row for filings, financial highlights, and sync status. Data is
          richer after you sync submissions or enrich records from filings.
        </p>
        <p className="meta-header-links">
          <Link className="nav-link" to="/">
            ← Dashboard search
          </Link>
        </p>
      </header>

      <main id="meta-main" className="meta-layout">
        {facetsErr && <p className="error">{facetsErr}</p>}

        {facets && (
          <section className="panel meta-summary" aria-labelledby="meta-summary-heading">
            <h2 id="meta-summary-heading">Coverage &amp; metrics</h2>
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

            <h3 className="subpanel-title">Top SIC descriptions</h3>
            <ul className="meta-bar-list" aria-label="Top SIC by company count">
              {facets.top_sic.slice(0, 12).map((row) => (
                <li key={`${row.sic_code}-${row.sic_description}`} className="meta-bar-row">
                  <button
                    type="button"
                    className="meta-bar-hit"
                    onClick={() => {
                      setSicCode(row.sic_code)
                      setPage(1)
                    }}
                    title="Filter table to this SIC code"
                  >
                    <span className="meta-bar-label">
                      {row.sic_code} — {row.sic_description}
                    </span>
                    <span className="meta-bar-track">
                      <span
                        className="meta-bar-fill"
                        style={{ width: `${(100 * row.count) / maxSicBar}%` }}
                      />
                    </span>
                    <span className="meta-bar-count">{row.count}</span>
                  </button>
                </li>
              ))}
            </ul>

            <div className="meta-facet-columns">
              <div>
                <h3 className="subpanel-title">HQ state (top)</h3>
                <ul className="meta-chip-list">
                  {facets.hq_state.slice(0, 12).map((row) => (
                    <li key={row.hq_state}>
                      <button
                        type="button"
                        className="meta-chip"
                        onClick={() => {
                          setHqState(row.hq_state)
                          setPage(1)
                        }}
                      >
                        {row.hq_state}{' '}
                        <span className="muted">({row.count})</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="subpanel-title">Industry text (top)</h3>
                <ul className="meta-chip-list">
                  {facets.industry.slice(0, 10).map((row) => (
                    <li key={row.industry}>
                      <button
                        type="button"
                        className="meta-chip meta-chip-wide"
                        onClick={() => {
                          setIndustryIcontains(row.industry.slice(0, 80))
                          setPage(1)
                        }}
                        title={row.industry}
                      >
                        {row.industry.length > 42 ? `${row.industry.slice(0, 40)}…` : row.industry}{' '}
                        <span className="muted">({row.count})</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        )}

        <section className="panel meta-filters" aria-labelledby="meta-filters-heading">
          <h2 id="meta-filters-heading">Filters</h2>
          <div className="meta-filter-grid">
            <label className="meta-field">
              <span className="meta-field-label">Search</span>
              <input
                className="input"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
                placeholder="Name, ticker, CIK, SIC text…"
              />
            </label>
            <label className="meta-field meta-field-sic">
              <span className="meta-field-label">SIC code</span>
              <div className="sic-autocomplete">
                <input
                  className="input"
                  value={sicCode}
                  onChange={(e) => {
                    setSicCode(e.target.value)
                    setPage(1)
                  }}
                  placeholder="Code or search title / office…"
                  autoComplete="off"
                  aria-autocomplete="list"
                  aria-controls="sic-suggest-list"
                  aria-expanded={sicSuggest.length > 0}
                  role="combobox"
                />
                {sicSuggest.length > 0 ? (
                  <ul id="sic-suggest-list" className="sic-suggest-list" role="listbox">
                    {sicSuggest.map((row) => (
                      <li key={row.code} role="option">
                        <button
                          type="button"
                          className="sic-suggest-item"
                          onMouseDown={(e) => e.preventDefault()}
                          onClick={() => {
                            setSicCode(row.code)
                            setSicPreview(`${row.industry_title} — ${row.office}`)
                            setSicSuggest([])
                            setPage(1)
                          }}
                        >
                          <span className="sic-suggest-code">{row.code}</span>
                          <span className="sic-suggest-title">{row.industry_title}</span>
                          <span className="sic-suggest-office">{row.office}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {sicPreview ? (
                  <p className="sic-preview" title={sicPreview}>
                    {sicPreview.length > 120 ? `${sicPreview.slice(0, 118)}…` : sicPreview}
                  </p>
                ) : null}
                <p className="meta-field-hint">
                  <a
                    href="https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list"
                    target="_blank"
                    rel="noreferrer"
                  >
                    SEC Standard Industrial Classification (SIC) code list
                  </a>
                </p>
              </div>
            </label>
            <label className="meta-field">
              <span className="meta-field-label">HQ state</span>
              <input
                className="input"
                value={hqState}
                onChange={(e) => {
                  setHqState(e.target.value)
                  setPage(1)
                }}
                placeholder="e.g. CA"
                maxLength={2}
              />
            </label>
            <label className="meta-field">
              <span className="meta-field-label">HQ country</span>
              <input
                className="input"
                value={hqCountry}
                onChange={(e) => {
                  setHqCountry(e.target.value)
                  setPage(1)
                }}
                placeholder="e.g. US"
                maxLength={2}
              />
            </label>
            <label className="meta-field meta-field-span2">
              <span className="meta-field-label">Industry contains</span>
              <input
                className="input"
                value={industryIcontains}
                onChange={(e) => {
                  setIndustryIcontains(e.target.value)
                  setPage(1)
                }}
              />
            </label>
            <label className="meta-field meta-field-span2">
              <span className="meta-field-label">SIC description contains</span>
              <input
                className="input"
                value={sicDescriptionIcontains}
                onChange={(e) => {
                  setSicDescriptionIcontains(e.target.value)
                  setPage(1)
                }}
              />
            </label>
            <label className="meta-field">
              <span className="meta-field-label">NAICS contains</span>
              <input
                className="input"
                value={naicsIcontains}
                onChange={(e) => {
                  setNaicsIcontains(e.target.value)
                  setPage(1)
                }}
              />
            </label>
            <label className="meta-field">
              <span className="meta-field-label">Rows per page</span>
              <select
                className="input meta-select"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value))
                  setPage(1)
                }}
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
              </select>
            </label>
          </div>
          <div className="meta-filter-actions">
            <button type="button" className="btn" onClick={() => void loadList()}>
              Refresh
            </button>
            <button type="button" className="btn" onClick={clearFilters}>
              Clear filters
            </button>
            <span className="muted small">
              {listCount.toLocaleString()} match
              {listCount === 1 ? '' : 'es'}
            </span>
          </div>
        </section>

        <section className="panel meta-table-panel" aria-labelledby="meta-table-heading">
          <h2 id="meta-table-heading" className="visually-hidden">
            Company table
          </h2>
          {listLoading && (
            <div className="spinner-row" role="status">
              <span className="spinner" aria-hidden />
              Loading…
            </div>
          )}
          {listErr && <p className="error">{listErr}</p>}
          {!listLoading && listCount === 0 && !listErr && (
            <div className="meta-empty-banner" role="status">
              <p className="meta-empty-title">No companies to show</p>
              <p className="muted small meta-empty-body">
                If the warehouse is empty, use{' '}
                <Link className="nav-link meta-empty-inline-link" to="/">
                  Dashboard → SEC issuer directory
                </Link>{' '}
                to add issuers, or load companies via the API / management commands.
              </p>
            </div>
          )}
          <div className="meta-table-wrap">
            <table className="meta-table">
              <thead>
                <tr>
                  <th scope="col">
                    <button type="button" className="th-sort" onClick={() => toggleSort('name')}>
                      Name{sortIndicator('name')}
                    </button>
                  </th>
                  <th scope="col">
                    <button type="button" className="th-sort" onClick={() => toggleSort('ticker')}>
                      Ticker{sortIndicator('ticker')}
                    </button>
                  </th>
                  <th scope="col">
                    <button type="button" className="th-sort" onClick={() => toggleSort('cik')}>
                      CIK{sortIndicator('cik')}
                    </button>
                  </th>
                  <th scope="col">
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => toggleSort('industry')}
                    >
                      Industry{sortIndicator('industry')}
                    </button>
                  </th>
                  <th scope="col">
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => toggleSort('sic_code')}
                    >
                      SIC{sortIndicator('sic_code')}
                    </button>
                  </th>
                  <th scope="col">SIC description</th>
                  <th scope="col">NAICS</th>
                  <th scope="col">
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => toggleSort('hq_state')}
                    >
                      St{sortIndicator('hq_state')}
                    </button>
                  </th>
                  <th scope="col">
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => toggleSort('hq_country')}
                    >
                      Ctry{sortIndicator('hq_country')}
                    </button>
                  </th>
                  <th scope="col">
                    <button type="button" className="th-sort" onClick={() => toggleSort('hq_city')}>
                      City{sortIndicator('hq_city')}
                    </button>
                  </th>
                  <th scope="col">
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => toggleSort('customer_vertical')}
                    >
                      Vertical{sortIndicator('customer_vertical')}
                    </button>
                  </th>
                  <th scope="col">
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => toggleSort('contract_status')}
                    >
                      Contract{sortIndicator('contract_status')}
                    </button>
                  </th>
                  <th scope="col">CRM key</th>
                  <th scope="col">Headquarters</th>
                  <th scope="col">Size</th>
                </tr>
              </thead>
              <tbody>
                {list.map((row) => (
                  <tr key={row.id}>
                    <td className="meta-td-name">
                      <Link
                        className="meta-company-link"
                        to={`/companies/${row.id}`}
                        title="Open company: filings, facts, sync status"
                      >
                        {row.name}
                      </Link>
                    </td>
                    <td>{row.ticker || '—'}</td>
                    <td className="meta-td-mono">{row.cik}</td>
                    <td className="meta-td-clip" title={row.industry || ''}>
                      {row.industry || '—'}
                    </td>
                    <td>{row.sic_code || '—'}</td>
                    <td className="meta-td-clip" title={row.sic_description || ''}>
                      {row.sic_description || '—'}
                    </td>
                    <td className="meta-td-mono">{row.naics_code || '—'}</td>
                    <td>{row.hq_state || '—'}</td>
                    <td>{row.hq_country || '—'}</td>
                    <td className="meta-td-clip">{row.hq_city || '—'}</td>
                    <td className="meta-td-clip" title={row.customer_vertical || ''}>
                      {row.customer_vertical || '—'}
                    </td>
                    <td className="meta-td-clip" title={row.contract_status || ''}>
                      {row.contract_status || '—'}
                    </td>
                    <td className="meta-td-mono meta-td-clip" title={row.crm_external_key || ''}>
                      {row.crm_external_key || '—'}
                    </td>
                    <td className="meta-td-clip" title={row.headquarters || ''}>
                      {row.headquarters || '—'}
                    </td>
                    <td className="meta-td-clip">{row.size || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <TablePager
            page={page}
            totalPages={totalPages}
            totalCount={listCount}
            onPageChange={setPage}
            disabled={listLoading}
          />
        </section>
      </main>
    </div>
  )
}
