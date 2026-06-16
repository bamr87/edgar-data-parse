import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  getAuthToken,
  getDerivedMetrics,
  getStatements,
  setAuthToken,
} from './api'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  localStorage.clear()
})

function mockFetch(data: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response)
  vi.stubGlobal('fetch', fn)
  return fn
}

describe('auth token storage', () => {
  it('round-trips and clears', () => {
    expect(getAuthToken()).toBe('')
    setAuthToken('abc123')
    expect(getAuthToken()).toBe('abc123')
    setAuthToken(null)
    expect(getAuthToken()).toBe('')
  })
})

describe('getStatements', () => {
  it('hits the statements endpoint and sends the auth header when a token is set', async () => {
    const fetchMock = mockFetch({
      company: 1,
      statement_type: 'income_statement',
      taxonomy: 'us-gaap',
      period_end: null,
      line_items: [],
    })
    setAuthToken('tok')

    await getStatements(1, 'income_statement')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/companies/1/statements/')
    expect(url).toContain('statement_type=income_statement')
    expect(init.headers).toMatchObject({ Authorization: 'Token tok' })
  })

  it('omits the auth header when no token is set', async () => {
    const fetchMock = mockFetch({ line_items: [] })
    await getStatements(5, 'balance_sheet')
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.headers).not.toHaveProperty('Authorization')
  })
})

describe('getDerivedMetrics', () => {
  it('filters by company and key', async () => {
    const fetchMock = mockFetch({ count: 0, next: null, previous: null, results: [] })
    await getDerivedMetrics(42, { key: 'gross_margin' })
    const [url] = fetchMock.mock.calls[0] as [string]
    expect(url).toContain('/api/v1/derived-metrics/')
    expect(url).toContain('company=42')
    expect(url).toContain('key=gross_margin')
  })
})
