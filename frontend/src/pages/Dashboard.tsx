/** Landing page: coverage overview + entry points into the rest of the app. */
import { Link, useNavigate } from 'react-router-dom'
import { useFacets } from '../lib/queries'
import { fullNum } from '../lib/format'
import { CompanySearch } from '../components/CompanySearch'
import {
  Card,
  CardHeader,
  IconBuilding,
  IconCompare,
  IconGlobe,
  IconSearch,
  IconUsers,
  Meter,
  Query,
  Stat,
} from '../components/ui'
import { BarsChart } from '../components/ui/Chart'

const QUICK_LINKS = [
  { to: '/companies', icon: <IconBuilding />, title: 'Company Explorer', desc: 'Filter & browse the warehouse' },
  { to: '/search', icon: <IconSearch />, title: 'Filing Search', desc: 'Full-text search of filing documents' },
  { to: '/compare', icon: <IconCompare />, title: 'Compare Cohorts', desc: 'Benchmark a metric across a group' },
  { to: '/macro', icon: <IconGlobe />, title: 'Macro Series', desc: 'FRED economic time series' },
]

export function Dashboard() {
  const facets = useFacets()
  const navigate = useNavigate()

  return (
    <div className="page">
      {/* Hero */}
      <Card className="card-pad" >
        <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center', padding: 'var(--sp-4) 0' }}>
          <h1 style={{ fontSize: 'var(--fs-3xl)' }}>Explore SEC company intelligence</h1>
          <p className="page-desc" style={{ margin: '8px auto var(--sp-4)', maxWidth: '58ch' }}>
            Filings, XBRL financials, derived KPIs, leadership, and a transparent stakeholder index —
            consolidated into a 360° view per company.
          </p>
          <div style={{ maxWidth: 560, margin: '0 auto' }}>
            <CompanySearch autoFocus />
          </div>
        </div>
      </Card>

      {/* Coverage stats */}
      <div className="grid grid-4 mt-5">
        <Query q={facets}>
          {(f) => (
            <>
              <Stat label="Companies" value={fullNum(f.totals.companies)} sub="in the warehouse" />
              <Stat label="With SIC code" value={fullNum(f.totals.with_sic_code)} sub={`${pctOf(f.totals.with_sic_code, f.totals.companies)} classified`} />
              <Stat label="With NAICS" value={fullNum(f.totals.with_naics_code)} sub={`${pctOf(f.totals.with_naics_code, f.totals.companies)} coverage`} />
              <Stat label="With industry text" value={fullNum(f.totals.with_industry_text)} sub={`${pctOf(f.totals.with_industry_text, f.totals.companies)} labeled`} />
            </>
          )}
        </Query>
      </div>

      {/* Quick links */}
      <div className="grid grid-4 mt-4">
        {QUICK_LINKS.map((l) => (
          <Link key={l.to} to={l.to} style={{ textDecoration: 'none', color: 'inherit' }}>
            <Card hover className="card-pad">
              <div className="row gap-3">
                <div className="brand-mark" style={{ background: 'var(--c-accent-soft)', color: 'var(--c-accent-text)' }}>{l.icon}</div>
                <div>
                  <div style={{ fontWeight: 650 }}>{l.title}</div>
                  <div className="caption">{l.desc}</div>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Breakdowns */}
      <div className="grid grid-2 mt-4">
        <Card>
          <CardHeader title="Top industries" sub="By SIC classification" icon={<IconBuilding width={16} height={16} />} />
          <Query q={facets} isEmpty={(f) => f.top_sic.length === 0} empty={<EmptyBlock />}>
            {(f) => (
              <div className="card-body col gap-3">
                {f.top_sic.slice(0, 8).map((s) => {
                  const max = f.top_sic[0]?.count || 1
                  return (
                    <Link key={s.sic_code} to={`/companies?sic_code=${encodeURIComponent(s.sic_code)}`} className="drill-row col gap-1" style={{ color: 'inherit', textDecoration: 'none' }}>
                      <div className="row between text-sm">
                        <span className="truncate drill-label" style={{ maxWidth: '70%' }}>{s.sic_description || `SIC ${s.sic_code}`}</span>
                        <span className="num muted">{fullNum(s.count)} ›</span>
                      </div>
                      <Meter value={s.count} max={max} />
                    </Link>
                  )
                })}
              </div>
            )}
          </Query>
        </Card>

        <Card>
          <CardHeader title="Headquarters by state" sub="Top regions" icon={<IconUsers width={16} height={16} />} />
          <Query q={facets} isEmpty={(f) => f.hq_state.length === 0} empty={<EmptyBlock />}>
            {(f) => (
              <div className="card-body">
                <div className="caption" style={{ marginBottom: 4 }}>Click a bar to view companies in that state.</div>
                <BarsChart
                  height={260}
                  data={f.hq_state.slice(0, 10).map((s) => ({ x: s.hq_state || '—', y: s.count }))}
                  fmt={(v) => fullNum(v)}
                  colorBy={(_p, i) => `var(--viz-${(i % 6) + 1})`}
                  onBarClick={(p) => p.x && p.x !== '—' && navigate(`/companies?hq_state=${encodeURIComponent(p.x)}`)}
                />
              </div>
            )}
          </Query>
        </Card>
      </div>
    </div>
  )
}

function pctOf(n: number, total: number): string {
  if (!total) return '0%'
  return `${Math.round((n / total) * 100)}%`
}

function EmptyBlock() {
  return (
    <div className="card-body">
      <div className="muted text-sm">No data yet. Add companies and sync filings from Settings.</div>
    </div>
  )
}
