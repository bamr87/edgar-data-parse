/** Browse & filter the company warehouse. URL-driven so any view can deep-link a
 *  filtered list (e.g. /companies?sic_code=3711 from a dashboard industry click). */
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useFacets, useMetadata } from '../lib/queries'
import { useDebounce } from '../lib/useDebounce'
import { useDocumentTitle } from '../lib/useDocumentTitle'
import { PageHeader } from '../components/PageHeader'
import { Pager } from '../components/Pager'
import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  IconBuilding,
  IconPlus,
  IconSearch,
  Query,
} from '../components/ui'
import type { CompanyMetadata } from '../lib/types'

const PAGE_SIZE = 40

// Filter params understood from the URL (label shown on the active-filter chip).
const FILTER_CHIPS: { key: string; label: string }[] = [
  { key: 'sic_code', label: 'SIC' },
  { key: 'sic_description', label: 'Industry' },
  { key: 'industry', label: 'Industry' },
  { key: 'hq_state', label: 'State' },
  { key: 'hq_country', label: 'Country' },
  { key: 'customer_vertical', label: 'Vertical' },
]

export function CompanyExplorer() {
  useDocumentTitle('Companies')
  const navigate = useNavigate()
  const facets = useFacets()
  const [params, setParams] = useSearchParams()

  const search = params.get('search') ?? ''
  const sic = params.get('sic_code') ?? ''
  const state = params.get('hq_state') ?? ''
  const ordering = params.get('ordering') ?? 'name'
  const page = Math.max(1, Number(params.get('page') ?? '1'))
  const debounced = useDebounce(search, 300)

  const list = useMetadata({
    page,
    page_size: PAGE_SIZE,
    search: debounced || undefined,
    sic_code: sic || undefined,
    sic_description: params.get('sic_description') || undefined,
    industry: params.get('industry') || undefined,
    hq_state: state || undefined,
    hq_country: params.get('hq_country') || undefined,
    customer_vertical: params.get('customer_vertical') || undefined,
    ordering,
  })

  /** Patch URL params (replace history so typing/filtering doesn't spam back-button). */
  function update(patch: Record<string, string>, opts: { resetPage?: boolean } = {}) {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    if (opts.resetPage !== false) next.delete('page')
    setParams(next, { replace: true })
  }

  const activeChips = FILTER_CHIPS.filter((c) => params.get(c.key))

  return (
    <div className="page">
      <PageHeader
        title="Companies"
        desc="Filter and browse every company in the warehouse. Click a row for the full 360° profile."
        actions={<Button variant="primary" onClick={() => navigate('/settings')}><IconPlus width={16} height={16} /> Add company</Button>}
      />

      {/* Filter bar */}
      <Card className="card-pad">
        <div className="row gap-3 wrap">
          <div className="search-box grow" style={{ minWidth: 240 }}>
            <IconSearch width={16} height={16} className="ico" />
            <input className="input" placeholder="Search name, ticker, CIK, industry…" value={search} onChange={(e) => update({ search: e.target.value })} />
          </div>
          <select className="select" style={{ width: 'auto' }} value={state} onChange={(e) => update({ hq_state: e.target.value })}>
            <option value="">All states</option>
            {facets.data?.hq_state.slice(0, 30).map((s) => <option key={s.hq_state} value={s.hq_state}>{s.hq_state} ({s.count})</option>)}
          </select>
          <select className="select" style={{ width: 'auto' }} value={sic} onChange={(e) => update({ sic_code: e.target.value })}>
            <option value="">All industries</option>
            {facets.data?.top_sic.slice(0, 25).map((s) => <option key={s.sic_code} value={s.sic_code}>{s.sic_description || s.sic_code}</option>)}
          </select>
          <select className="select" style={{ width: 'auto' }} value={ordering} onChange={(e) => update({ ordering: e.target.value })}>
            <option value="name">Name A–Z</option>
            <option value="-name">Name Z–A</option>
            <option value="-created_at">Newest</option>
            <option value="ticker">Ticker</option>
          </select>
        </div>

        {/* Active-filter chips — make every deep-linked filter visible + clearable. */}
        {activeChips.length > 0 && (
          <div className="row gap-2 wrap mt-3">
            <span className="caption">Filters:</span>
            {activeChips.map((c) => (
              <button key={c.key} className="badge badge-accent" style={{ cursor: 'pointer' }} title="Remove filter" onClick={() => update({ [c.key]: '' })}>
                {c.label}: {sicLabel(c.key, params.get(c.key)!, facets.data?.top_sic)} ✕
              </button>
            ))}
            <button className="link-btn text-sm" onClick={() => setParams(new URLSearchParams(search ? { search } : {}), { replace: true })}>Clear all</button>
          </div>
        )}
      </Card>

      <div className="mt-4">
        <Card>
          <Query q={list} isEmpty={(d) => d.results.length === 0} empty={<EmptyState icon={<IconBuilding />} title="No companies match" message="Try a different filter, or add a company from SEC in Settings." />}>
            {(d) => (
              <>
                <div className="caption" style={{ padding: 'var(--sp-3) var(--sp-4) 0' }}>{d.count.toLocaleString()} companies</div>
                <DataTable<CompanyMetadata>
                  rows={d.results}
                  rowKey={(r) => r.id}
                  onRowClick={(r) => navigate(`/companies/${r.id}`)}
                  columns={[
                    {
                      key: 'name', header: 'Company',
                      render: (r) => (
                        <div className="row gap-3">
                          <div className="brand-mark" style={{ width: 30, height: 30, fontSize: 12, background: 'var(--c-surface-3)', color: 'var(--c-text-muted)' }}>
                            {(r.ticker || r.name).slice(0, 2).toUpperCase()}
                          </div>
                          <div className="grow" style={{ minWidth: 0 }}>
                            <div className="truncate" style={{ fontWeight: 600 }}>{r.name}</div>
                            <div className="caption mono">CIK {r.cik}</div>
                          </div>
                        </div>
                      ),
                    },
                    { key: 'ticker', header: 'Ticker', render: (r) => r.ticker ? <Badge tone="accent">{r.ticker}</Badge> : <span className="subtle">—</span> },
                    {
                      key: 'industry', header: 'Industry',
                      render: (r) => r.sic_code
                        ? <button className="link-btn text-sm" onClick={(e) => { e.stopPropagation(); update({ sic_code: r.sic_code! }) }}>{r.sic_description || r.sic_code}</button>
                        : <span className="text-sm">{r.industry || '—'}</span>,
                    },
                    {
                      key: 'hq', header: 'HQ',
                      render: (r) => r.hq_state
                        ? <button className="link-btn text-sm" onClick={(e) => { e.stopPropagation(); update({ hq_state: r.hq_state! }) }}>{[r.hq_state, r.hq_country].filter(Boolean).join(', ')}</button>
                        : <span className="text-sm">{r.hq_country || '—'}</span>,
                    },
                    { key: 'vertical', header: 'Vertical', render: (r) => r.customer_vertical ? <Badge>{r.customer_vertical}</Badge> : '' },
                  ]}
                />
                <Pager page={page} count={d.count} pageSize={PAGE_SIZE} onPage={(p) => update({ page: String(p) }, { resetPage: false })} />
              </>
            )}
          </Query>
        </Card>
      </div>
    </div>
  )
}

/** Show the human SIC description on a sic_code chip when we can resolve it from facets. */
function sicLabel(key: string, value: string, topSic?: { sic_code: string; sic_description: string }[]): string {
  if (key === 'sic_code') {
    const hit = topSic?.find((s) => s.sic_code === value)
    return hit?.sic_description || value
  }
  return value
}
