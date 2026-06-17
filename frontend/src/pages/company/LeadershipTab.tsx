/** Leadership roster + transparent stakeholder-orientation index + grounded AI analysis. */
import { useApp } from '../../lib/app-context'
import { useAnalyzeLeadership, useLeadership, useLeadershipAnalysis, useStakeholder } from '../../lib/queries'
import { date, signed } from '../../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DataTable,
  EmptyState,
  IconSparkle,
  Query,
} from '../../components/ui'
import type { LeadershipPerson } from '../../lib/types'

export function LeadershipTab({ id }: { id: number }) {
  return (
    <div className="col gap-4">
      <StakeholderCard id={id} />
      <RosterCard id={id} />
      <AnalysisCard id={id} />
    </div>
  )
}

function orientationColor(idx: number | null): string {
  if (idx == null) return 'var(--c-text-subtle)'
  if (idx >= 0.33) return 'var(--c-positive)'
  if (idx <= -0.33) return 'var(--c-negative)'
  return 'var(--c-warning)'
}

function StakeholderCard({ id }: { id: number }) {
  const stakeholder = useStakeholder(id)
  return (
    <Card>
      <CardHeader title="Stakeholder orientation" sub="People-vs-profits capital-allocation index — a transparent heuristic, not a rating" icon={<IconSparkle width={16} height={16} />} />
      <Query q={stakeholder} isEmpty={(s) => s.orientation_index == null} empty={<EmptyState title="Insufficient data" message="Needs XBRL facts (capex, R&D, buybacks, dividends, revenue) to compute. Sync facts first." />}>
        {(s) => (
          <div className="card-body col gap-4">
            <div className="row gap-4 wrap">
              <div className="stat" style={{ padding: 0, flex: 1, minWidth: 220 }}>
                <div className="stat-label">Orientation index</div>
                <div className="stat-value" style={{ color: orientationColor(s.orientation_index) }}>
                  {s.orientation_index?.toFixed(2)}
                </div>
                <div className="row gap-2 mt-2">
                  <Badge tone={s.orientation_index != null && s.orientation_index >= 0.33 ? 'pos' : s.orientation_index != null && s.orientation_index <= -0.33 ? 'neg' : 'warn'}>
                    {s.label}
                  </Badge>
                  {s.period_end && <span className="caption">period ending {date(s.period_end)}</span>}
                </div>
              </div>
              <div style={{ flex: 2, minWidth: 260 }}>
                <div className="row between caption"><span>Payout / shareholder</span><span>Reinvestment / stakeholder</span></div>
                <div className="meter mt-2" style={{ height: 12 }}>
                  <div className="meter-fill" style={{
                    marginLeft: `${(((s.orientation_index ?? 0) + 1) / 2) * 100 - 1}%`,
                    width: 3, background: orientationColor(s.orientation_index), height: '100%',
                  }} />
                </div>
                <div className="caption mt-1" style={{ textAlign: 'center' }}>−1 to +1 scale</div>
              </div>
            </div>

            {/* Signal breakdown */}
            <div className="table-wrap">
              <table className="tbl tbl-compact">
                <thead><tr><th>Signal</th><th className="td-num">Value</th><th className="td-num">Score</th><th className="td-num">Weight</th></tr></thead>
                <tbody>
                  {s.signals.map((sig) => (
                    <tr key={sig.name}>
                      <td><div>{sig.label}</div><div className="caption">{sig.note}</div></td>
                      <td className="td-num">{sig.value}</td>
                      <td className="td-num" style={{ color: sig.score >= 0 ? 'var(--c-positive)' : 'var(--c-negative)' }}>{sig.score.toFixed(2)}</td>
                      <td className="td-num">{Math.round(sig.weight * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="caption" style={{ lineHeight: 1.6, background: 'var(--c-surface-2)', padding: 'var(--sp-3)', borderRadius: 'var(--radius-sm)' }}>
              <strong>Methodology &amp; caveats:</strong> {s.caveats}
            </p>
          </div>
        )}
      </Query>
    </Card>
  )
}

function RosterCard({ id }: { id: number }) {
  const leadership = useLeadership(id)
  return (
    <Card>
      <CardHeader title="Leadership roster" sub="Officers, directors & owners from SEC Forms 3/4/5" />
      <Query q={leadership} isEmpty={(l) => l.leadership.length === 0} empty={<EmptyState title="No leadership extracted" message="Run sync_leadership (CLI) after syncing Forms 3/4/5 filings." />}>
        {(l) => (
          <DataTable<LeadershipPerson>
            rows={l.leadership}
            rowKey={(r, i) => `${r.name}-${i}`}
            initialSort={{ key: 'filings', dir: 'desc' }}
            columns={[
              { key: 'name', header: 'Name', render: (r) => <span style={{ fontWeight: 600 }}>{r.name}</span>, sortable: true, sortValue: (r) => r.name },
              { key: 'title', header: 'Title', render: (r) => r.title || '—' },
              {
                key: 'roles', header: 'Roles', render: (r) => (
                  <div className="row gap-1 wrap">
                    {r.is_officer && <Badge tone="accent">Officer</Badge>}
                    {r.is_director && <Badge tone="info">Director</Badge>}
                    {r.is_ten_percent_owner && <Badge tone="warn">10% owner</Badge>}
                  </div>
                ),
              },
              { key: 'tenure', header: 'Tenure (filing range)', render: (r) => `${date(r.first_seen)} – ${date(r.last_seen)}` },
              { key: 'filings', header: 'Filings', align: 'right', render: (r) => r.filings_count, sortable: true, sortValue: (r) => r.filings_count },
              {
                key: 'shares', header: 'Net insider Δ', align: 'right',
                render: (r) => <span style={{ color: r.net_insider_shares >= 0 ? 'var(--c-positive)' : 'var(--c-negative)' }}>{signed(r.net_insider_shares)}</span>,
                sortable: true, sortValue: (r) => r.net_insider_shares,
              },
            ]}
          />
        )}
      </Query>
    </Card>
  )
}

function AnalysisCard({ id }: { id: number }) {
  const { isAdmin } = useApp()
  const analysis = useLeadershipAnalysis(id)
  const analyze = useAnalyzeLeadership(id)

  return (
    <Card>
      <CardHeader
        title="AI leadership analysis"
        sub="Initiatives, verbatim quotes & direction — grounded strictly in SEC filing text"
        icon={<IconSparkle width={16} height={16} />}
        actions={isAdmin ? <Button size="sm" variant="primary" loading={analyze.isPending} onClick={() => analyze.mutate()}>Run analysis</Button> : undefined}
      />
      <Query q={analysis}>
        {(a) => {
          if (a.available === false || (!a.summary && a.initiatives.length === 0 && a.quotes.length === 0)) {
            return (
              <EmptyState
                title={a.enabled === false ? 'AI analysis is disabled' : 'No analysis yet'}
                message={a.enabled === false
                  ? 'Set ENABLE_AI_ANALYSIS=true and configure ANTHROPIC_API_KEY on the backend.'
                  : isAdmin ? 'Click “Run analysis” to generate a grounded summary from ingested filings.' : 'An admin can generate this from ingested filings.'}
              />
            )
          }
          return (
            <div className="card-body col gap-4">
              {a.summary && <p style={{ lineHeight: 1.6 }}>{a.summary}</p>}
              {a.direction && (
                <div><span className="field-label">Stated direction</span><p className="mt-1" style={{ lineHeight: 1.6 }}>{a.direction}</p></div>
              )}
              {a.initiatives.length > 0 && (
                <div>
                  <span className="field-label">Initiatives</span>
                  <div className="col gap-2 mt-2">
                    {a.initiatives.map((it, i) => (
                      <div key={i} className="card card-pad" style={{ background: 'var(--c-surface-2)' }}>
                        <div className="row between gap-2"><strong>{it.title}</strong>{it.source && <Badge>{it.source}</Badge>}</div>
                        <p className="caption mt-1" style={{ lineHeight: 1.6 }}>{it.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {a.quotes.length > 0 && (
                <div>
                  <span className="field-label">Verbatim quotes</span>
                  <div className="col gap-2 mt-2">
                    {a.quotes.map((qt, i) => (
                      <blockquote key={i} style={{ margin: 0, borderLeft: '3px solid var(--c-accent)', padding: '4px 0 4px 12px' }}>
                        <p style={{ fontStyle: 'italic', lineHeight: 1.6 }}>“{qt.text}”</p>
                        <span className="caption">{qt.speaker ? `— ${qt.speaker} · ` : ''}{qt.source}</span>
                      </blockquote>
                    ))}
                  </div>
                </div>
              )}
              <p className="caption" style={{ lineHeight: 1.6, background: 'var(--c-warning-soft)', color: 'var(--c-warning)', padding: 'var(--sp-3)', borderRadius: 'var(--radius-sm)' }}>
                {a.caveats}
              </p>
              {a.model_name && <span className="caption">Model: {a.model_name}{a.created_at ? ` · ${date(a.created_at)}` : ''}</span>}
            </div>
          )
        }}
      </Query>
      {analyze.isError && <div className="caption neg" style={{ padding: '0 var(--sp-4) var(--sp-4)' }}>{(analyze.error as Error).message}</div>}
    </Card>
  )
}
