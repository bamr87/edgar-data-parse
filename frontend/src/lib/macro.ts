/** Pure helpers for the macro workspace: range windows, transforms (level / YoY /
 *  index=100), and period-change stats. Frequency-agnostic via date-based lookups. */
import type { BundleObservations } from './types'

export type RawPoint = { date: string; value: number }
export type ChartPoint = { x: string; y: number | null }
export type RangeKey = '1' | '3' | '5' | '10' | 'max'
export type Transform = 'level' | 'yoy' | 'index'

export const RANGE_OPTIONS: { value: RangeKey; label: string }[] = [
  { value: '1', label: '1Y' },
  { value: '3', label: '3Y' },
  { value: '5', label: '5Y' },
  { value: '10', label: '10Y' },
  { value: 'max', label: 'Max' },
]

export const TRANSFORM_OPTIONS: { value: Transform; label: string; hint: string }[] = [
  { value: 'level', label: 'Level', hint: 'Raw reported values' },
  { value: 'yoy', label: 'YoY %', hint: 'Year-over-year percent change' },
  { value: 'index', label: 'Index=100', hint: 'Rebased to 100 at the window start' },
]

/** Extract a single series' sorted numeric points from a bundle-observations payload. */
export function seriesPoints(obs: BundleObservations, seriesId: string): RawPoint[] {
  return obs.observations
    .filter((o) => o.series === seriesId)
    .map((o) => ({ date: o.date, value: Number(o.value) }))
    .filter((p) => Number.isFinite(p.value))
    .sort((a, b) => a.date.localeCompare(b.date))
}

function shift(dateStr: string, opts: { years?: number; days?: number }): string {
  const d = new Date(`${dateStr}T00:00:00`)
  if (opts.years) d.setFullYear(d.getFullYear() + opts.years)
  if (opts.days) d.setDate(d.getDate() + opts.days)
  return d.toISOString().slice(0, 10)
}

export function rangeCutoff(range: RangeKey): string | null {
  if (range === 'max') return null
  const d = new Date()
  d.setFullYear(d.getFullYear() - Number(range))
  return d.toISOString().slice(0, 10)
}

export function applyRange(points: RawPoint[], range: RangeKey): RawPoint[] {
  const cut = rangeCutoff(range)
  return cut ? points.filter((p) => p.date >= cut) : points
}

/** Nearest point to `target` date within `tolDays`, searching points[0..hi]. */
function nearest(points: RawPoint[], target: string, hi: number, tolDays = 45): RawPoint | null {
  // binary search for insertion index of target among points[0..hi]
  let lo = 0
  let h = hi
  while (lo < h) {
    const mid = (lo + h) >> 1
    if (points[mid].date < target) lo = mid + 1
    else h = mid
  }
  const candidates = [points[lo - 1], points[lo]].filter(Boolean) as RawPoint[]
  let best: RawPoint | null = null
  let bestDiff = Infinity
  const t = new Date(`${target}T00:00:00`).getTime()
  for (const c of candidates) {
    const diff = Math.abs(new Date(`${c.date}T00:00:00`).getTime() - t)
    if (diff < bestDiff) {
      bestDiff = diff
      best = c
    }
  }
  return best && bestDiff <= tolDays * 86400000 ? best : null
}

/** Transform points to chart-ready values. */
export function applyTransform(points: RawPoint[], t: Transform): ChartPoint[] {
  if (points.length === 0) return []
  if (t === 'level') return points.map((p) => ({ x: p.date, y: p.value }))
  if (t === 'index') {
    const base = points.find((p) => p.value !== 0)?.value
    return points.map((p) => ({ x: p.date, y: base ? (p.value / base) * 100 : null }))
  }
  // YoY %: compare to the value ~1 year earlier (nearest by date).
  return points.map((p, i) => {
    const prev = nearest(points, shift(p.date, { years: -1 }), i)
    return { x: p.date, y: prev && prev.value !== 0 ? (p.value / prev.value - 1) * 100 : null }
  })
}

export type Change = { abs: number | null; pct: number | null }

/** Change of the latest value vs the value ~`days` ago (absolute + percent). */
export function changeOver(points: RawPoint[], days: number): Change {
  if (points.length < 2) return { abs: null, pct: null }
  const last = points[points.length - 1]
  const prev = nearest(points, shift(last.date, { days: -days }), points.length - 1, days < 60 ? 20 : 50)
  if (!prev) return { abs: null, pct: null }
  return { abs: last.value - prev.value, pct: prev.value !== 0 ? (last.value / prev.value - 1) * 100 : null }
}

export type SeriesStats = {
  latest: number
  latestDate: string
  min: number
  max: number
  chg1m: Change
  chg3m: Change
  chg1y: Change
}

export function seriesStats(points: RawPoint[]): SeriesStats | null {
  if (points.length === 0) return null
  const latest = points[points.length - 1]
  const values = points.map((p) => p.value)
  return {
    latest: latest.value,
    latestDate: latest.date,
    min: Math.min(...values),
    max: Math.max(...values),
    chg1m: changeOver(points, 30),
    chg3m: changeOver(points, 92),
    chg1y: changeOver(points, 365),
  }
}

/** A rate/percent-unit series (show absolute point change, not % change). */
export function isRateUnit(units: string | undefined): boolean {
  const u = (units || '').toLowerCase()
  return u.includes('percent') || u.trim() === '%'
}
