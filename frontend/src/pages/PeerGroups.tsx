/** Peer groups + peer-fact comparison for a chosen concept. */
import { useState } from 'react'
import { usePeerFactCompare, usePeerGroups } from '../lib/queries'
import { money } from '../lib/format'
import { useDocumentTitle } from '../lib/useDocumentTitle'
import { PageHeader } from '../components/PageHeader'
import {
  Card,
  CardHeader,
  DataTable,
  EmptyState,
  IconGroup,
  Query,
} from '../components/ui'
import { BarsChart } from '../components/ui/Chart'
import type { PeerFactCompare } from '../lib/types'

const CONCEPTS = [
  { value: 'Revenues', label: 'Revenue' },
  { value: 'NetIncomeLoss', label: 'Net Income' },
  { value: 'Assets', label: 'Total Assets' },
  { value: 'ResearchAndDevelopmentExpense', label: 'R&D Expense' },
]

export function PeerGroups() {
  useDocumentTitle('Peer Groups')
  const groups = usePeerGroups()
  const [selected, setSelected] = useState<number | null>(null)
  const [concept, setConcept] = useState('Revenues')
  const compare = usePeerFactCompare(selected, concept)

  return (
    <div className="page">
      <PageHeader title="Peer Groups" desc="Curated peer sets and side-by-side fact comparison across their members." />

      <div className="grid" style={{ gridTemplateColumns: '300px 1fr', alignItems: 'start' }}>
        <Card>
          <CardHeader title="Groups" icon={<IconGroup width={16} height={16} />} />
          <Query q={groups} isEmpty={(g) => g.results.length === 0} empty={<EmptyState title="No peer groups" message="Create peer groups via the API/admin." />}>
            {(g) => (
              <div className="col" style={{ padding: 6 }}>
                {g.results.map((pg) => (
                  <button key={pg.id} className={`combo-item ${selected === pg.id ? 'active' : ''}`} onClick={() => setSelected(pg.id)}>
                    <div className="grow">
                      <div style={{ fontWeight: 600 }}>{pg.name}</div>
                      {pg.description && <div className="caption truncate">{pg.description}</div>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Query>
        </Card>

        <div className="col gap-4">
          {selected == null ? (
            <Card><EmptyState icon={<IconGroup />} title="Select a peer group" message="Pick a group on the left to compare a concept across its members." /></Card>
          ) : (
            <>
              <Card className="card-pad">
                <label className="field" style={{ maxWidth: 280 }}>
                  <span className="field-label">Concept</span>
                  <select className="select" value={concept} onChange={(e) => setConcept(e.target.value)}>
                    {CONCEPTS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </label>
              </Card>
              <Query q={compare} isEmpty={(d) => d.rows.length === 0} empty={<EmptyState title="No data" message="Members have no facts for this concept yet." />}>
                {(d) => (
                  <>
                    <Card>
                      <CardHeader title="Comparison" />
                      <div className="card-body">
                        <BarsChart height={280} data={d.rows.map((r) => ({ x: r.ticker || r.name, y: r.value }))} fmt={(v) => money(v)} colorBy={(_p, i) => `var(--viz-${(i % 6) + 1})`} />
                      </div>
                    </Card>
                    <Card>
                      <DataTable<PeerFactCompare['rows'][number]>
                        rows={d.rows}
                        rowKey={(r) => r.cik}
                        initialSort={{ key: 'value', dir: 'desc' }}
                        columns={[
                          { key: 'name', header: 'Company', render: (r) => <div><div style={{ fontWeight: 600 }}>{r.name}</div><div className="caption mono">{r.ticker || `CIK ${r.cik}`}</div></div> },
                          { key: 'value', header: CONCEPTS.find((c) => c.value === concept)?.label ?? concept, align: 'right', render: (r) => money(r.value), sortable: true, sortValue: (r) => r.value ?? -Infinity },
                          { key: 'period', header: 'Period', align: 'right', render: (r) => r.period_end ?? '—' },
                        ]}
                      />
                    </Card>
                  </>
                )}
              </Query>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
