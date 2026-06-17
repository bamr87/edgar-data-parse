/** Global full-text search across ingested filing documents. */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useDocumentSearch } from '../lib/queries'
import { useDebounce } from '../lib/useDebounce'
import { cikInt } from '../lib/format'
import { useCompanyIdByCik } from '../lib/lookup'
import { PageHeader } from '../components/PageHeader'
import {
  Badge,
  Card,
  EmptyState,
  IconSearch,
  Query,
} from '../components/ui'

export function FilingSearch() {
  const [q, setQ] = useState('')
  const [formType, setFormType] = useState('')
  const [cik, setCik] = useState('')
  const debounced = useDebounce(q, 350)
  const results = useDocumentSearch({ q: debounced, form_type: formType || undefined, cik: cik || undefined })

  return (
    <div className="page">
      <PageHeader
        title="Filing Search"
        desc="Full-text search across ingested SEC filing documents. Postgres ranks by relevance; SQLite falls back to substring match."
      />

      <Card className="card-pad">
        <div className="row gap-3 wrap">
          <div className="search-box grow" style={{ minWidth: 280 }}>
            <IconSearch width={16} height={16} className="ico" />
            <input className="input" autoFocus placeholder="Search filing text — e.g. “climate risk”, “stock repurchase”…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <select className="select" style={{ width: 'auto' }} value={formType} onChange={(e) => setFormType(e.target.value)}>
            <option value="">All forms</option>
            {['10-K', '10-Q', '8-K', 'DEF 14A', 'S-1'].map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
          <input className="input" style={{ width: 160 }} placeholder="CIK (optional)" value={cik} onChange={(e) => setCik(e.target.value)} />
        </div>
        <div className="caption mt-2">Type at least 2 characters to search.</div>
      </Card>

      {debounced.trim().length >= 2 && (
        <div className="mt-4">
          <Query q={results} isEmpty={(d) => d.results.length === 0} empty={<EmptyState icon={<IconSearch />} title="No matches" message="No ingested documents match. Ingest full submissions (admin) to grow the corpus." />}>
            {(d) => (
              <div className="col gap-3">
                <span className="caption">{d.count} match{d.count === 1 ? '' : 'es'} for “{d.query}”</span>
                {d.results.map((h) => (
                  <Card key={h.id} hover className="card-pad">
                    <div className="row between wrap gap-2">
                      <div className="row gap-2 wrap">
                        <Badge tone="info">{h.form_type || h.type}</Badge>
                        {h.file_name && <span className="caption mono">{h.file_name}</span>}
                        <span className="caption">CIK {cikInt(h.cik)}</span>
                      </div>
                      <CompanyLink cik={h.cik} />
                    </div>
                    <p className="mt-2" style={{ lineHeight: 1.6, color: 'var(--c-text-muted)' }}>…{h.snippet}…</p>
                  </Card>
                ))}
              </div>
            )}
          </Query>
        </div>
      )}
    </div>
  )
}

/** Resolve the warehouse company id from a CIK so we can deep-link to the 360 page. */
function CompanyLink({ cik }: { cik: string }) {
  const id = useCompanyIdByCik(cik)
  if (id.data == null) return null
  return <Link to={`/companies/${id.data}`} className="text-sm">View company →</Link>
}
