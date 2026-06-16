/** Cross-company analytics: cohort metric benchmarking + leadership orientation compare. */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { leadershipCompare } from '../lib/api'
import { useCohortCompare } from '../lib/queries'
import { compact, fullNum, money } from '../lib/format'
import { PageHeader } from '../components/PageHeader'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DataTable,
  EmptyState,
  Query,
  Tabs,
} from '../components/ui'
import { BarsChart } from '../components/ui/Chart'
import type { CohortGroupRow, LeadershipCompareRow } from '../lib/types'

const CONCEPTS = [
  { value: 'Revenues', label: 'Revenue' },
  { value: 'NetIncomeLoss', label: 'Net Income' },
  { value: 'Assets', label: 'Total Assets' },
  { value: 'ResearchAndDevelopmentExpense', label: 'R&D Expense' },
  { value: 'PaymentsToAcquirePropertyPlantAndEquipment', label: 'Capex' },
]
const GROUP_BY = [
  { value: 'sic_description', label: 'Industry (SIC)' },
  { value: 'hq_state', label: 'HQ state' },
  { value: 'hq_country', label: 'HQ country' },
  { value: 'industry', label: 'Industry (text)' },
  { value: 'customer_vertical', label: 'Customer vertical' },
]

export function Compare() {
  const [tab, setTab] = useState('cohort')
  return (
    <div className="page">
      <PageHeader title="Compare" desc="Benchmark a financial concept across a cohort, or compare leadership orientation across companies." />
      <Tabs tabs={[{ key: 'cohort', label: 'Cohort metrics' }, { key: 'leadership', label: 'Leadership orientation' }]} value={tab} onChange={setTab} />
      <div className="mt-4">{tab === 'cohort' ? <CohortCompare /> : <LeadershipCompareView />}</div>
    </div>
  )
}

function CohortCompare() {
  const [concept, setConcept] = useState('Revenues')
  const [groupBy, setGroupBy] = useState('sic_description')
  const q = useCohortCompare({ concept, group_by: groupBy })

  return (
    <div className="col gap-4">
      <Card className="card-pad">
        <div className="row gap-3 wrap">
          <label className="field" style={{ flex: 1, minWidth: 200 }}>
            <span className="field-label">Concept</span>
            <select className="select" value={concept} onChange={(e) => setConcept(e.target.value)}>
              {CONCEPTS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </label>
          <label className="field" style={{ flex: 1, minWidth: 200 }}>
            <span className="field-label">Group by</span>
            <select className="select" value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              {GROUP_BY.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </label>
        </div>
      </Card>

      <Query q={q} isEmpty={(d) => d.groups.length === 0} empty={<EmptyState title="No cohort data" message="No companies have facts for this concept yet." />}>
        {(d) => {
          const top = [...d.groups].sort((a, b) => b.avg - a.avg).slice(0, 12)
          return (
            <>
              <Card>
                <CardHeader title={`Average ${CONCEPTS.find((c) => c.value === concept)?.label ?? concept} by ${GROUP_BY.find((g) => g.value === groupBy)?.label}`} />
                <div className="card-body">
                  <BarsChart height={300} data={top.map((g) => ({ x: g.group || '—', y: g.avg }))} fmt={(v) => money(v)} colorBy={(_p, i) => `var(--viz-${(i % 6) + 1})`} />
                </div>
              </Card>
              <Card>
                <CardHeader title="Cohort breakdown" />
                <DataTable<CohortGroupRow>
                  rows={d.groups}
                  rowKey={(r) => r.group || 'na'}
                  initialSort={{ key: 'count', dir: 'desc' }}
                  columns={[
                    { key: 'group', header: 'Group', render: (r) => r.group || '—', sortable: true, sortValue: (r) => r.group || '' },
                    { key: 'count', header: 'Companies', align: 'right', render: (r) => fullNum(r.company_count), sortable: true, sortValue: (r) => r.company_count },
                    { key: 'avg', header: 'Average', align: 'right', render: (r) => money(r.avg), sortable: true, sortValue: (r) => r.avg },
                    { key: 'min', header: 'Min', align: 'right', render: (r) => compact(r.min) },
                    { key: 'max', header: 'Max', align: 'right', render: (r) => compact(r.max) },
                    { key: 'sum', header: 'Total', align: 'right', render: (r) => money(r.sum), sortable: true, sortValue: (r) => r.sum },
                  ]}
                />
              </Card>
            </>
          )
        }}
      </Query>
    </div>
  )
}

function LeadershipCompareView() {
  const [raw, setRaw] = useState('')
  const [ciks, setCiks] = useState<string[]>([])
  const q = useQuery({
    queryKey: ['leadership-compare', ciks],
    queryFn: () => leadershipCompare(ciks),
    enabled: ciks.length > 0,
  })

  return (
    <div className="col gap-4">
      <Card className="card-pad">
        <span className="field-label">Compare by CIK</span>
        <div className="row gap-2 wrap mt-1">
          <input className="input grow" style={{ minWidth: 260 }} placeholder="Comma-separated CIKs, e.g. 0001318605, 0000037996" value={raw} onChange={(e) => setRaw(e.target.value)} />
          <Button variant="primary" onClick={() => setCiks(raw.split(',').map((c) => c.trim()).filter(Boolean))}>Compare</Button>
        </div>
        <div className="caption mt-2">Compares leadership footprint + the transparent stakeholder-orientation index side by side.</div>
      </Card>

      {ciks.length > 0 && (
        <Query q={q} isEmpty={(d) => d.results.length === 0} empty={<EmptyState title="No companies found" message="Check the CIKs — companies must already be in the warehouse." />}>
          {(d) => (
            <Card>
              <CardHeader title="Leadership comparison" />
              <DataTable<LeadershipCompareRow>
                rows={d.results}
                rowKey={(r) => r.cik}
                columns={[
                  { key: 'name', header: 'Company', render: (r) => <div><div style={{ fontWeight: 600 }}>{r.name}</div><div className="caption mono">{r.ticker || `CIK ${r.cik}`}</div></div> },
                  { key: 'count', header: 'Leaders', align: 'right', render: (r) => r.leadership_count },
                  { key: 'people', header: 'Key people', render: (r) => <div className="row gap-1 wrap">{r.key_people.slice(0, 3).map((p, i) => <Badge key={i}>{p.name}</Badge>)}</div> },
                  {
                    key: 'orient', header: 'Orientation', align: 'right',
                    render: (r) => (
                      <Badge tone={r.orientation_index != null && r.orientation_index >= 0.33 ? 'pos' : r.orientation_index != null && r.orientation_index <= -0.33 ? 'neg' : 'warn'}>
                        {r.orientation_index?.toFixed(2) ?? '—'} {r.orientation_label}
                      </Badge>
                    ),
                  },
                ]}
              />
              <p className="caption" style={{ padding: 'var(--sp-3) var(--sp-4)' }}>{d.caveats}</p>
            </Card>
          )}
        </Query>
      )}
    </div>
  )
}
