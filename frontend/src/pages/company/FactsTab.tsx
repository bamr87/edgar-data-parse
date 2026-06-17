/** XBRL fact facets + a searchable, paginated facts table. */
import { useState } from 'react'
import { useFacts, useFactsFacets } from '../../lib/queries'
import { byUnit, date, fullNum } from '../../lib/format'
import { downloadCsv } from '../../lib/csv'
import { useDebounce } from '../../lib/useDebounce'
import { Pager } from '../../components/Pager'
import {
  Button,
  Card,
  CardHeader,
  DataTable,
  EmptyState,
  IconDownload,
  IconSearch,
  Query,
  SkeletonTable,
} from '../../components/ui'
import { BarsChart } from '../../components/ui/Chart'
import type { Fact } from '../../lib/types'

const PAGE_SIZE = 50

export function FactsTab({ id }: { id: number }) {
  const facets = useFactsFacets(id)
  const [page, setPage] = useState(1)
  const [concept, setConcept] = useState('')
  const debounced = useDebounce(concept, 300)
  const facts = useFacts({ company: id, page, concept: debounced || undefined })

  return (
    <div className="col gap-4">
      {/* Facets */}
      <div className="grid grid-3">
        <Card>
          <CardHeader title="Facts by year" />
          <div className="card-body">
            <Query q={facets} isEmpty={(f) => f.facts_by_period_year.length === 0} empty={<MiniEmpty />}>
              {(f) => (
                <BarsChart height={200} data={f.facts_by_period_year.map((y) => ({ x: String(y.year), y: y.count }))} fmt={(v) => fullNum(v)} />
              )}
            </Query>
          </div>
        </Card>
        <Card>
          <CardHeader title="Top concepts" />
          <Query q={facets} isEmpty={(f) => f.top_concepts.length === 0} empty={<MiniEmpty />}>
            {(f) => (
              <div className="card-body col gap-2">
                {f.top_concepts.slice(0, 8).map((c) => (
                  <button key={c.concept} className="row between text-sm link-btn" style={{ textAlign: 'left' }} onClick={() => { setConcept(c.concept); setPage(1) }}>
                    <span className="truncate mono" style={{ maxWidth: '75%' }}>{c.concept}</span>
                    <span className="num muted">{fullNum(c.c)}</span>
                  </button>
                ))}
              </div>
            )}
          </Query>
        </Card>
        <Card>
          <CardHeader title="Taxonomies" />
          <Query q={facets} isEmpty={(f) => f.taxonomy_counts.length === 0} empty={<MiniEmpty />}>
            {(f) => (
              <div className="card-body col gap-2">
                {f.taxonomy_counts.map((t) => (
                  <div key={t.taxonomy} className="row between text-sm"><span className="badge badge-accent">{t.taxonomy}</span><span className="num muted">{fullNum(t.c)}</span></div>
                ))}
              </div>
            )}
          </Query>
        </Card>
      </div>

      {/* Facts table */}
      <Card>
        <CardHeader
          title="XBRL facts"
          actions={
            <div className="row gap-2">
              <div className="search-box" style={{ width: 220 }}>
                <IconSearch width={16} height={16} className="ico" />
                <input className="input" placeholder="Filter by concept…" value={concept} onChange={(e) => { setConcept(e.target.value); setPage(1) }} />
              </div>
              <Button
                size="sm" variant="ghost" title="Download this page (CSV)"
                disabled={!facts.data?.results.length}
                onClick={() => facts.data && downloadCsv(`facts-p${page}.csv`, facts.data.results.map((r) => ({ concept: r.concept, taxonomy: r.taxonomy, period_start: r.period_start, period_end: r.period_end, unit: r.unit, value: r.value })))}
              >
                <IconDownload width={14} height={14} />
              </Button>
            </div>
          }
        />
        <Query q={facts} pending={<SkeletonTable />} isEmpty={(f) => f.results.length === 0} empty={<EmptyState title="No facts" message="Sync facts (admin) to populate XBRL data." />}>
          {(f) => (
            <>
              <DataTable<Fact>
                compact
                rows={f.results}
                rowKey={(r) => r.id}
                columns={[
                  { key: 'concept', header: 'Concept', render: (r) => <span className="mono text-sm">{r.concept}</span> },
                  { key: 'tax', header: 'Taxonomy', render: (r) => <span className="caption">{r.taxonomy}</span> },
                  { key: 'period', header: 'Period', render: (r) => `${date(r.period_start)} – ${date(r.period_end)}` },
                  { key: 'unit', header: 'Unit', render: (r) => <span className="caption">{r.unit || '—'}</span> },
                  { key: 'value', header: 'Value', align: 'right', render: (r) => byUnit(r.value, r.unit) },
                ]}
              />
              <Pager page={page} count={f.count} pageSize={PAGE_SIZE} onPage={setPage} />
            </>
          )}
        </Query>
      </Card>
    </div>
  )
}

function MiniEmpty() {
  return <div className="card-body"><span className="muted text-sm">No facts yet.</span></div>
}
