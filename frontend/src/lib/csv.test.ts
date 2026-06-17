import { describe, expect, it } from 'vitest'
import { toCsv } from './csv'

describe('toCsv', () => {
  it('builds a header + rows from objects', () => {
    const csv = toCsv([{ a: 1, b: 'x' }, { a: 2, b: 'y' }])
    expect(csv).toBe('a,b\n1,x\n2,y')
  })
  it('respects an explicit column order', () => {
    const csv = toCsv([{ a: 1, b: 2 }], ['b', 'a'])
    expect(csv).toBe('b,a\n2,1')
  })
  it('quotes values containing commas, quotes, or newlines', () => {
    const csv = toCsv([{ x: 'a,b', y: 'he said "hi"', z: 'line\nbreak' }])
    expect(csv).toBe('x,y,z\n"a,b","he said ""hi""","line\nbreak"')
  })
  it('renders null/undefined as empty', () => {
    const csv = toCsv([{ a: null, b: undefined, c: 0 }])
    expect(csv).toBe('a,b,c\n,,0')
  })
  it('returns empty string for no rows', () => {
    expect(toCsv([])).toBe('')
  })
  it('neutralizes formula injection in text cells but leaves numbers intact', () => {
    // =/+/@/- leading text cells get a guard apostrophe; the numeric -5 does not.
    const csv = toCsv([{ name: '=cmd()', note: '+1', amt: -5 }])
    expect(csv).toBe("name,note,amt\n'=cmd(),'+1,-5")
  })
})
