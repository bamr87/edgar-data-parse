/** Recently-viewed companies, persisted to localStorage (most-recent first). */
import { useCallback, useEffect, useState } from 'react'

export type RecentCompany = { id: number; name: string; ticker: string | null; cik: string }
const KEY = 'edgarRecentCompanies'
const MAX = 8

function read(): RecentCompany[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as RecentCompany[]) : []
  } catch {
    return []
  }
}

/** Record a company as recently viewed (call on the detail page). */
export function recordRecent(c: RecentCompany) {
  try {
    const next = [c, ...read().filter((x) => x.id !== c.id)].slice(0, MAX)
    localStorage.setItem(KEY, JSON.stringify(next))
    window.dispatchEvent(new Event('edgar-recent-changed'))
  } catch {
    /* private mode */
  }
}

/** Reactive list of recently-viewed companies. */
export function useRecentCompanies(): RecentCompany[] {
  const [list, setList] = useState<RecentCompany[]>(read)
  const refresh = useCallback(() => setList(read()), [])
  useEffect(() => {
    window.addEventListener('edgar-recent-changed', refresh)
    window.addEventListener('storage', refresh)
    return () => {
      window.removeEventListener('edgar-recent-changed', refresh)
      window.removeEventListener('storage', refresh)
    }
  }, [refresh])
  return list
}
