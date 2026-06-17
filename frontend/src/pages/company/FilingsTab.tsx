/** Filings list + full-text document search scoped to this company. */
import { useState } from 'react'
import { useDocumentSearch, useFilings } from '../../lib/queries'
import { date, secFilingUrl } from '../../lib/format'
import { useDebounce } from '../../lib/useDebounce'
import { Pager } from '../../components/Pager'
import {
  Badge,
  Card,
  CardHeader,
  DataTable,
  EmptyState,
  IconExternal,
  IconSearch,
  Query,
  SkeletonTable,
} from '../../components/ui'
import type { Filing } from '../../lib/types'

const PAGE_SIZE = 25

export function FilingsTab({ id, cik }: { id: number; cik: string }) {
  const [page, setPage] = useState(1)
  const [formType, setFormType] = useState('')
  const filings = useFilings({ company: id, page, form_type: formType || undefined })

  const [docQ, setDocQ] = useState('')
  const debouncedQ = useDebounce(docQ, 300)
  const docs = useDocumentSearch({ q: debouncedQ, cik })

  return (
    <div className="col gap-4">
      {/* Document full-text search */}
      <Card>
        <CardHeader title="Search filing text" sub="Full-text search across this company’s ingested documents" />
        <div className="card-body">
          <div className="search-box" style={{ maxWidth: 480 }}>
            <IconSearch width={16} height={16} className="ico" />
            <input className="input" placeholder="e.g. risk factors, supply chain, revenue recognition…" value={docQ} onChange={(e) => setDocQ(e.target.value)} />
          </div>
          {debouncedQ.trim().length >= 2 && (
            <div className="mt-3">
              <Query q={docs} isEmpty={(d) => d.results.length === 0} empty={<EmptyState title="No matches" message="No ingested documents match. Ingest a full submission first (admin)." />}>
                {(d) => (
                  <div className="col gap-2">
                    <span className="caption">{d.count} match{d.count === 1 ? '' : 'es'}</span>
                    {d.results.slice(0, 20).map((h) => (
                      <div key={h.id} className="card card-pad" style={{ background: 'var(--c-surface-2)' }}>
                        <div className="row gap-2 wrap">
                          <Badge tone="info">{h.form_type || h.type}</Badge>
                          {h.file_name && <span className="caption mono">{h.file_name}</span>}
                        </div>
                        <p className="caption mt-2" style={{ lineHeight: 1.6 }}>…{h.snippet}…</p>
                      </div>
                    ))}
                  </div>
                )}
              </Query>
            </div>
          )}
        </div>
      </Card>

      {/* Filings list */}
      <Card>
        <CardHeader
          title="Filings"
          actions={
            <select className="select" style={{ width: 'auto' }} value={formType} onChange={(e) => { setFormType(e.target.value); setPage(1) }}>
              <option value="">All forms</option>
              {['10-K', '10-Q', '8-K', '4', '3', '5', 'DEF 14A', 'S-1'].map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          }
        />
        <Query q={filings} pending={<SkeletonTable />} isEmpty={(f) => f.results.length === 0} empty={<EmptyState title="No filings" message="Sync filings from the admin bar above." />}>
          {(f) => (
            <>
              <DataTable<Filing>
                rows={f.results}
                rowKey={(r) => r.id}
                columns={[
                  { key: 'form', header: 'Form', render: (r) => <Badge tone="info">{r.form_type}</Badge> },
                  { key: 'acc', header: 'Accession', render: (r) => <span className="mono text-sm">{r.accession_number}</span> },
                  { key: 'filed', header: 'Filed', render: (r) => date(r.filing_date), sortable: true, sortValue: (r) => r.filing_date || '' },
                  { key: 'period', header: 'Period', render: (r) => date(r.period_of_report) },
                  {
                    key: 'link', header: '', align: 'right',
                    render: (r) => <a href={r.url || secFilingUrl(cik, r.accession_number)} target="_blank" rel="noreferrer" className="row gap-1" style={{ justifyContent: 'flex-end' }}>open <IconExternal width={12} height={12} /></a>,
                  },
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
