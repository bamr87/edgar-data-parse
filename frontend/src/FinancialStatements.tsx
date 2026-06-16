import { useEffect, useState } from 'react'
import {
  getStatements,
  type FinancialStatement,
  type StatementType,
} from './api'

const TABS: { key: StatementType; label: string }[] = [
  { key: 'income_statement', label: 'Income' },
  { key: 'balance_sheet', label: 'Balance Sheet' },
  { key: 'cash_flow_statement', label: 'Cash Flow' },
]

function fmt(v: number | null): string {
  if (v == null) return '—'
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(v)
}

function secArchiveUrl(cik: string | undefined, accession: string | null): string | null {
  if (!cik || !accession) return null
  const noDashes = accession.replace(/-/g, '')
  const cikDigits = cik.replace(/^0+/, '') || cik
  return `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cikDigits}&type=&dateb=&owner=include&count=40&search_text=${noDashes}`
}

export type FinancialStatementsProps = {
  companyId: number
  cik?: string
}

/** Balance/Income/Cash-Flow tabs rendered from the latest period's resolved facts. */
export default function FinancialStatements({ companyId, cik }: FinancialStatementsProps) {
  const [tab, setTab] = useState<StatementType>('income_statement')
  const [stmt, setStmt] = useState<FinancialStatement | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const data = await getStatements(companyId, tab)
        if (!cancelled) setStmt(data)
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e))
          setStmt(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [companyId, tab])

  return (
    <section className="panel detail-panel fa-statements" aria-labelledby="detail-stmt-h">
      <h2 id="detail-stmt-h">Financial statements</h2>
      <p className="dash-hint">
        Latest-period line items mapped from XBRL facts via the reference statement schema. Each
        value links to its source filing for verification.
      </p>
      <div className="fa-stmt-tabs" role="tablist" aria-label="Statement type">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={tab === t.key ? 'fa-chip fa-chip-active' : 'fa-chip'}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
      {loading && (
        <p className="muted" role="status">
          Loading statement…
        </p>
      )}
      {!loading && !error && stmt && (
        <>
          <p className="muted small">Period end: {stmt.period_end ?? '—'}</p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Line item</th>
                  <th scope="col" className="fa-history-num">
                    Value
                  </th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                {stmt.line_items.map((li) => {
                  const url = secArchiveUrl(cik, li.accession)
                  return (
                    <tr key={li.key}>
                      <td>{li.label}</td>
                      <td className="fa-history-num">{fmt(li.value)}</td>
                      <td>
                        {li.accession ? (
                          url ? (
                            <a href={url} target="_blank" rel="noreferrer">
                              {li.accession}
                            </a>
                          ) : (
                            li.accession
                          )
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
