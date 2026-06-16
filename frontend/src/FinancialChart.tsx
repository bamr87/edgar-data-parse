import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ConceptTimeseriesPoint } from './api'

export type FinancialChartProps = {
  series: ConceptTimeseriesPoint[]
  height?: number
  label?: string
}

const compact = (v: number) =>
  new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(v)

/** Line chart of a concept's value over time (oldest -> newest). Reuses the
 * same `ConceptTimeseriesPoint[]` the period-history table already fetched. */
export default function FinancialChart({ series, height = 260, label }: FinancialChartProps) {
  const data = series
    .filter((p) => p.value != null && p.period_end)
    .map((p) => ({ period: p.period_end as string, value: p.value as number }))
    .sort((a, b) => (a.period < b.period ? -1 : a.period > b.period ? 1 : 0))

  if (data.length === 0) {
    return <p className="muted">No chartable values for this concept.</p>
  }

  return (
    <div
      className="fa-chart"
      role="img"
      aria-label={label ? `${label} trend chart` : 'Concept trend chart'}
    >
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #e2e2e2)" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={72} tickFormatter={compact} />
          <Tooltip
            formatter={(v) => new Intl.NumberFormat().format(v as number)}
            labelFormatter={(l) => `Period end ${l}`}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--accent, #2563eb)"
            strokeWidth={2}
            dot={{ r: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
