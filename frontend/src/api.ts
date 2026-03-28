const base =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || ''

/** localStorage key; overrides VITE_SEC_USER_AGENT_EMAIL when set */
export const SEC_USER_AGENT_EMAIL_STORAGE_KEY = 'edgarSecUserAgentEmail'

/** Contact email sent as `X-Sec-User-Agent-Email` on SEC-related API calls. */
export function getResolvedSecUserAgentEmail(): string {
  try {
    const fromStore = localStorage
      .getItem(SEC_USER_AGENT_EMAIL_STORAGE_KEY)
      ?.trim()
    if (fromStore) return fromStore
  } catch {
    /* private mode */
  }
  return import.meta.env.VITE_SEC_USER_AGENT_EMAIL?.trim() || ''
}

function secHeaders(): Record<string, string> {
  const email = getResolvedSecUserAgentEmail()
  if (!email) return {}
  return { 'X-Sec-User-Agent-Email': email }
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${base}${path}`, { headers: { ...secHeaders() } })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

export async function apiPost<T>(path: string, body?: object): Promise<T> {
  const r = await fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...secHeaders() },
    body: body ? JSON.stringify(body) : '{}',
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

export type Company = {
  id: number
  cik: string
  ticker: string | null
  name: string
  industry: string | null
  sic_code: string | null
  sic_description: string | null
  hq_state: string | null
}

/** Full company row from `GET /api/v1/companies/:id/` (serializer uses all model fields). */
export type CompanyRecord = Company & {
  naics_code: string | null
  hq_country: string
  hq_city: string | null
  headquarters: string | null
  size: string | null
  extra_attributes: Record<string, unknown>
  management: Record<string, unknown>
  locations: unknown[]
  business_units: unknown[]
  product_types: unknown[]
  crm_external_key: string | null
  customer_class: string | null
  customer_type: string | null
  customer_vertical: string | null
  contract_status: string | null
  created_at: string
  updated_at: string
}

export type FacetsResponse = {
  totals: {
    companies: number
    with_sic_code: number
    with_naics_code: number
    with_industry_text: number
  }
  top_sic: { sic_code: string; sic_description: string; count: number }[]
  hq_state: { hq_state: string; count: number }[]
  industry: { industry: string; count: number }[]
  hq_country: { hq_country: string; count: number }[]
}

export type CompanyMetadataListResponse = {
  count: number
  next: string | null
  previous: string | null
  results: {
    id: number
    cik: string
    ticker: string | null
    name: string
    industry: string | null
    sic_code: string | null
    sic_description: string | null
    naics_code: string | null
    hq_state: string | null
    hq_country: string
    hq_city: string | null
    headquarters: string | null
    size: string | null
    crm_external_key: string | null
    customer_class: string | null
    customer_type: string | null
    customer_vertical: string | null
    contract_status: string | null
    created_at: string
    updated_at: string
  }[]
}

export type EdgarSearchResult = {
  cik: string
  ticker: string | null
  name: string
  in_warehouse: boolean
}

export type EdgarSearchResponse = {
  count: number
  results: EdgarSearchResult[]
}

/** Row from ``GET /api/v1/reference/sic-codes/`` (SEC master SIC table). */
export type SicReferenceRow = {
  code: string
  office: string
  industry_title: string
}

export type SicReferenceResponse = {
  count: number
  results: SicReferenceRow[]
}

/** Search SEC SIC reference: use ``q`` for typeahead, ``code`` for exact match. */
export function fetchSicCodes(params: {
  q?: string
  code?: string
  limit?: number
}): Promise<SicReferenceResponse> {
  const u = new URLSearchParams()
  if (params.q?.trim()) u.set('q', params.q.trim())
  if (params.code?.trim()) u.set('code', params.code.trim())
  u.set('limit', String(params.limit ?? 40))
  return apiGet<SicReferenceResponse>(`/api/v1/reference/sic-codes/?${u}`)
}

export type FromEdgarBody = {
  ticker?: string | null
  cik?: string | number | null
  name?: string | null
}

export type EdgarSyncStatusResponse = {
  company: number
  submissions_synced_at: string | null
  facts_synced_at: string | null
  last_error: string
}

export type AnalyticsLatestValue = {
  concept: string
  period_end: string | null
  period_start: string | null
  value: number | null
  unit: string | null
  dimensions: Record<string, unknown>
}

export type AnalyticsLatestByConceptsResponse = {
  company: number
  taxonomy: string
  values: Record<string, AnalyticsLatestValue>
}

export type FilingRecord = {
  id: number
  company: number
  accession_number: string
  form_type: string
  filing_date: string | null
  period_of_report: string | null
  url: string | null
  local_path: string | null
  metadata: Record<string, unknown>
}

/** Paginated filings list from `GET /api/v1/filings/`. */
export type FilingListPaginatedResponse = {
  count: number
  next: string | null
  previous: string | null
  results: FilingRecord[]
}

export function unwrapArray<T>(data: T[] | { results: T[] }): T[] {
  if (Array.isArray(data)) return data
  return data.results
}

/** Listed issuers matching `q` (min 2 chars on server). */
export function edgarCompanySearch(q: string, limit = 50): Promise<EdgarSearchResponse> {
  const u = new URLSearchParams()
  u.set('q', q.trim())
  u.set('limit', String(limit))
  return apiGet<EdgarSearchResponse>(`/api/v1/companies/edgar-search/?${u}`)
}

export function companyFromEdgar(body: FromEdgarBody): Promise<CompanyRecord> {
  return apiPost<CompanyRecord>('/api/v1/companies/from-edgar/', body)
}

export function getCompany(id: number): Promise<CompanyRecord> {
  return apiGet<CompanyRecord>(`/api/v1/companies/${id}/`)
}

export function getEdgarSyncStatus(id: number): Promise<EdgarSyncStatusResponse> {
  return apiGet<EdgarSyncStatusResponse>(`/api/v1/companies/${id}/edgar-sync-status/`)
}

export type SyncSubmissionsResponse = {
  company: number
  filings_processed: number
}

export type SyncFactsResponse = {
  company: number
  facts_loaded: number
}

/** POST: fetch SEC submissions index for this company and upsert Filing rows. */
export function syncCompanySubmissions(id: number): Promise<SyncSubmissionsResponse> {
  return apiPost<SyncSubmissionsResponse>(`/api/v1/companies/${id}/sync-submissions/`)
}

/** POST: fetch SEC companyfacts JSON and load Fact rows. */
export function syncCompanyFacts(id: number): Promise<SyncFactsResponse> {
  return apiPost<SyncFactsResponse>(`/api/v1/companies/${id}/sync-facts/`)
}

export function getFacets(): Promise<FacetsResponse> {
  return apiGet<FacetsResponse>('/api/v1/company-metadata/facets/')
}

export function searchCompanyMetadata(params: {
  search: string
  page_size: number
}): Promise<CompanyMetadataListResponse> {
  const u = new URLSearchParams()
  u.set('page', '1')
  u.set('page_size', String(params.page_size))
  if (params.search.trim()) u.set('search', params.search.trim())
  return apiGet<CompanyMetadataListResponse>(`/api/v1/company-metadata/?${u}`)
}

/** Resolve warehouse company id by CIK (exact filter on list endpoint). */
export async function findCompanyIdByCik(cik: string): Promise<number | null> {
  const u = new URLSearchParams()
  u.set('cik', cik.trim())
  const data = await apiGet<CompanyRecord[] | { results: CompanyRecord[] }>(
    `/api/v1/companies/?${u}`,
  )
  const rows = unwrapArray(data)
  return rows[0]?.id ?? null
}

function normalizeFilingsResponse(
  raw: unknown,
  page: number,
  pageSize: number,
  search?: string,
): FilingListPaginatedResponse {
  if (Array.isArray(raw)) {
    let rows = raw as FilingRecord[]
    const q = search?.trim().toLowerCase()
    if (q) {
      rows = rows.filter(
        (f) =>
          (f.form_type && f.form_type.toLowerCase().includes(q)) ||
          (f.accession_number && f.accession_number.toLowerCase().includes(q)),
      )
    }
    const count = rows.length
    const start = Math.max(0, (page - 1) * pageSize)
    const results = rows.slice(start, start + pageSize)
    return { count, next: null, previous: null, results }
  }
  if (raw && typeof raw === 'object' && 'results' in raw) {
    const r = raw as FilingListPaginatedResponse
    const results = Array.isArray(r.results) ? r.results : []
    const count = typeof r.count === 'number' ? r.count : results.length
    return {
      count,
      next: r.next ?? null,
      previous: r.previous ?? null,
      results,
    }
  }
  return { count: 0, next: null, previous: null, results: [] }
}

export async function getFilingsForCompany(
  companyId: number,
  opts?: {
    page?: number
    page_size?: number
    ordering?: string
    search?: string
  },
): Promise<FilingListPaginatedResponse> {
  const page = opts?.page ?? 1
  const pageSize = opts?.page_size ?? 25
  const u = new URLSearchParams()
  u.set('company', String(companyId))
  u.set('page', String(page))
  u.set('page_size', String(pageSize))
  if (opts?.ordering) u.set('ordering', opts.ordering)
  if (opts?.search?.trim()) u.set('search', opts.search.trim())
  const raw = await apiGet<unknown>(`/api/v1/filings/?${u}`)
  return normalizeFilingsResponse(raw, page, pageSize, opts?.search)
}

export function getLatestByConcepts(
  companyId: number,
  concepts: string[],
  taxonomy = 'us-gaap',
): Promise<AnalyticsLatestByConceptsResponse> {
  const u = new URLSearchParams()
  u.set('concepts', concepts.join(','))
  u.set('taxonomy', taxonomy)
  return apiGet<AnalyticsLatestByConceptsResponse>(
    `/api/v1/companies/${companyId}/analytics/latest-by-concepts/?${u}`,
  )
}
