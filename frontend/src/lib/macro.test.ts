import { describe, expect, it } from 'vitest'
import { applyTransform, changeOver, isRateUnit, seriesStats, type RawPoint } from './macro'

// Monthly-ish points: value doubles over 12 steps.
const monthly: RawPoint[] = Array.from({ length: 25 }, (_, i) => ({
  date: `20${24 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, '0')}-01`,
  value: 100 + i * 10,
}))

describe('applyTransform', () => {
  it('level passes values through', () => {
    const out = applyTransform(monthly, 'level')
    expect(out[0].y).toBe(100)
    expect(out[out.length - 1].y).toBe(340)
  })
  it('index rebases to 100 at the window start', () => {
    const out = applyTransform(monthly, 'index')
    expect(out[0].y).toBe(100)
    expect(out[12].y).toBeCloseTo((220 / 100) * 100, 5)
  })
  it('yoy computes year-over-year percent change', () => {
    const out = applyTransform(monthly, 'yoy')
    // first 12 months have no 1y-prior point
    expect(out[0].y).toBeNull()
    // month 12 (value 220) vs month 0 (value 100) => +120%
    expect(out[12].y).toBeCloseTo(120, 1)
  })
})

describe('changeOver', () => {
  it('returns absolute and percent change', () => {
    const c = changeOver(monthly, 365)
    expect(c.abs).not.toBeNull()
    expect(c.pct).not.toBeNull()
    expect((c.pct as number) > 0).toBe(true)
  })
})

describe('seriesStats', () => {
  it('reports latest / min / max', () => {
    const s = seriesStats(monthly)!
    expect(s.latest).toBe(340)
    expect(s.min).toBe(100)
    expect(s.max).toBe(340)
  })
  it('handles empty input', () => {
    expect(seriesStats([])).toBeNull()
  })
})

describe('isRateUnit', () => {
  it('detects percent units', () => {
    expect(isRateUnit('Percent')).toBe(true)
    expect(isRateUnit('Billions of Dollars')).toBe(false)
  })
})
