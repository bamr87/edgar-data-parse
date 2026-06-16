/** Browse & filter the company warehouse (company-metadata + facets). */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFacets, useMetadata } from '../lib/queries'
import { useDebounce } from '../lib/useDebounce'
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

export function CompanyExplorer() {
  const navigate = useNavigate()
  const facets = useFacets()
  const [search, setSearch] = useState('')
  const [state, setState] = useState('')
  const [sic, setSic] = useState('')
  const [ordering, setOrdering] = useState('name')
  const [page, setPage] = useState(1)
  const debounced = useDebounce(search, 300)

  const list = useMetadata({
    page,
    page_size: PAGE_SIZE,
    search: debounced || undefined,
    hq_state: state || undefined,
    sic_code: sic || undefined,
    ordering,
  })

  function reset(setter: (v: string) => void, v: string) {
    setter(v)
    setPage(1)
  }

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
            <input className="input" placeholder="Search name, ticker, CIK, industry…" value={search} onChange={(e) => reset(setSearch, e.target.value)} />
          </div>
          <select className="select" style={{ width: 'auto' }} value={state} onChange={(e) => reset(setState, e.target.value)}>
            <option value="">All states</option>
            {facets.data?.hq_state.slice(0, 30).map((s) => <option key={s.hq_state} value={s.hq_state}>{s.hq_state} ({s.count})</option>)}
          </select>
          <select className="select" style={{ width: 'auto' }} value={sic} onChange={(e) => reset(setSic, e.target.value)}>
            <option value="">All industries</option>
            {facets.data?.top_sic.slice(0, 25).map((s) => <option key={s.sic_code} value={s.sic_code}>{s.sic_description || s.sic_code}</option>)}
          </select>
          <select className="select" style={{ width: 'auto' }} value={ordering} onChange={(e) => setOrdering(e.target.value)}>
            <option value="name">Name A–Z</option>
            <option value="-name">Name Z–A</option>
            <option value="-created_at">Newest</option>
            <option value="ticker">Ticker</option>
          </select>
        </div>
      </Card>

      <div className="mt-4">
        <Card>
          <Query q={list} isEmpty={(d) => d.results.length === 0} empty={<EmptyState icon={<IconBuilding />} title="No companies match" message="Try a different filter, or add a company from SEC in Settings." />}>
            {(d) => (
              <>
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
                    { key: 'industry', header: 'Industry', render: (r) => <span className="text-sm">{r.sic_description || r.industry || '—'}</span> },
                    { key: 'hq', header: 'HQ', render: (r) => <span className="text-sm">{[r.hq_state, r.hq_country].filter(Boolean).join(', ') || '—'}</span> },
                    { key: 'vertical', header: 'Vertical', render: (r) => r.customer_vertical ? <Badge>{r.customer_vertical}</Badge> : '' },
                  ]}
                />
                <Pager page={page} count={d.count} pageSize={PAGE_SIZE} onPage={setPage} />
              </>
            )}
          </Query>
        </Card>
      </div>
    </div>
  )
}
