/** Client-side CSV export — build a CSV from rows and trigger a download. */
export function toCsv(rows: Record<string, unknown>[], columns?: string[]): string {
  if (rows.length === 0) return ''
  const cols = columns ?? Object.keys(rows[0])
  const esc = (v: unknown) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  return [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n')
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[], columns?: string[]): void {
  const csv = toCsv(rows, columns)
  if (!csv) return
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
