/** Themed recharts wrappers. Colors use CSS variables so they follow the theme. */
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { compact } from '../../lib/format'

export type Point = { x: string; y: number | null }

const axisTick = { fill: 'var(--c-text-subtle)', fontSize: 11 }
const gridStroke = 'var(--c-border)'

type TooltipItem = { name?: string; value?: number; color?: string }
type TooltipProps = { active?: boolean; label?: string | number; payload?: TooltipItem[]; fmt?: (v: number) => string }

function ChartTooltip({ active, payload, label, fmt }: TooltipProps) {
  if (!active || !payload?.length) return null
  const f = fmt || compact
  return (
    <div className="card" style={{ padding: '8px 10px', boxShadow: 'var(--shadow)', fontSize: 12 }}>
      <div className="subtle" style={{ marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="row gap-2" style={{ justifyContent: 'space-between' }}>
          <span className="row gap-1"><span className="dot" style={{ color: p.color }} />{p.name}</span>
          <span className="num">{f(p.value ?? 0)}</span>
        </div>
      ))}
    </div>
  )
}

export function TrendChart({
  data,
  color = 'var(--c-accent)',
  area = true,
  height = 240,
  fmt,
}: {
  data: Point[]
  color?: string
  area?: boolean
  height?: number
  fmt?: (v: number) => string
}) {
  const fmtY = (v: number) => compact(v)
  return (
    <ResponsiveContainer width="100%" height={height}>
      {area ? (
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="g-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
          <XAxis dataKey="x" tick={axisTick} tickLine={false} axisLine={{ stroke: gridStroke }} minTickGap={24} />
          <YAxis tick={axisTick} tickLine={false} axisLine={false} tickFormatter={fmtY} width={52} />
          <Tooltip content={(p) => <ChartTooltip {...(p as unknown as TooltipProps)} fmt={fmt} />} />
          <Area type="monotone" dataKey="y" name="value" stroke={color} strokeWidth={2} fill="url(#g-area)" connectNulls dot={false} />
        </AreaChart>
      ) : (
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
          <XAxis dataKey="x" tick={axisTick} tickLine={false} axisLine={{ stroke: gridStroke }} minTickGap={24} />
          <YAxis tick={axisTick} tickLine={false} axisLine={false} tickFormatter={fmtY} width={52} />
          <Tooltip content={(p) => <ChartTooltip {...(p as unknown as TooltipProps)} fmt={fmt} />} />
          <Line type="monotone" dataKey="y" name="value" stroke={color} strokeWidth={2} connectNulls dot={false} />
        </LineChart>
      )}
    </ResponsiveContainer>
  )
}

export function BarsChart({
  data,
  height = 240,
  fmt,
  colorBy,
}: {
  data: Point[]
  height?: number
  fmt?: (v: number) => string
  colorBy?: (p: Point, i: number) => string
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
        <XAxis dataKey="x" tick={axisTick} tickLine={false} axisLine={{ stroke: gridStroke }} minTickGap={8} />
        <YAxis tick={axisTick} tickLine={false} axisLine={false} tickFormatter={(v) => compact(v)} width={52} />
        <Tooltip cursor={{ fill: 'var(--c-surface-2)' }} content={(p) => <ChartTooltip {...(p as unknown as TooltipProps)} fmt={fmt} />} />
        <Bar dataKey="y" name="value" radius={[4, 4, 0, 0]}>
          {data.map((p, i) => (
            <Cell key={i} fill={colorBy ? colorBy(p, i) : 'var(--c-accent)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export function Sparkline({ data, color = 'var(--c-accent)', height = 40 }: { data: Point[]; color?: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 2, left: 2, bottom: 2 }}>
        <Line type="monotone" dataKey="y" stroke={color} strokeWidth={1.6} dot={false} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  )
}
