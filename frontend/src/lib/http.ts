/**
 * HTTP core for the Django API (`/api/v1`). Centralizes base URL, auth + SEC
 * User-Agent headers, and structured error handling. All feature code goes
 * through `api.ts` (which uses these), never `fetch` directly.
 */

const BASE = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || ''

export const SEC_EMAIL_KEY = 'edgarSecUserAgentEmail'
export const AUTH_TOKEN_KEY = 'edgarAuthToken'

function readLS(key: string): string {
  try {
    return localStorage.getItem(key)?.trim() || ''
  } catch {
    return ''
  }
}

export function getSecEmail(): string {
  return readLS(SEC_EMAIL_KEY) || import.meta.env.VITE_SEC_USER_AGENT_EMAIL?.trim() || ''
}

export function getAuthToken(): string {
  return readLS(AUTH_TOKEN_KEY)
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
    else localStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    /* private mode */
  }
}

export function setSecEmail(email: string | null): void {
  try {
    if (email) localStorage.setItem(SEC_EMAIL_KEY, email)
    else localStorage.removeItem(SEC_EMAIL_KEY)
  } catch {
    /* private mode */
  }
}

/** Structured API error: carries HTTP status + the server's `detail` message. */
export class ApiError extends Error {
  status: number
  detail: string
  body: unknown
  constructor(status: number, detail: string, body: unknown) {
    super(detail || `HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.body = body
  }
  /** True for 401/403 — caller likely needs an admin token. */
  get isAuth(): boolean {
    return this.status === 401 || this.status === 403
  }
  get isRateLimit(): boolean {
    return this.status === 429
  }
}

function headers(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...extra }
  const token = getAuthToken()
  if (token) h.Authorization = `Token ${token}`
  const email = getSecEmail()
  if (email) h['X-Sec-User-Agent-Email'] = email
  return h
}

async function parse(r: Response): Promise<unknown> {
  const ct = r.headers.get('content-type') || ''
  if (ct.includes('application/json')) return r.json()
  return r.text()
}

async function handle<T>(r: Response): Promise<T> {
  if (r.ok) return (await parse(r)) as T
  const body = await parse(r)
  let detail = `Request failed (${r.status})`
  if (body && typeof body === 'object' && 'detail' in body) {
    detail = String((body as { detail: unknown }).detail)
  } else if (typeof body === 'string' && body) {
    detail = body.slice(0, 300)
  }
  throw new ApiError(r.status, detail, body)
}

export async function httpGet<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { headers: headers() })
  return handle<T>(r)
}

export async function httpPost<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: headers({ 'Content-Type': 'application/json' }),
    body: body ? JSON.stringify(body) : '{}',
  })
  return handle<T>(r)
}

/** Build a query string from a params object, skipping null/undefined/''. */
export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    u.set(k, String(v))
  }
  const s = u.toString()
  return s ? `?${s}` : ''
}
