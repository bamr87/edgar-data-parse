import { Button } from './ui'
import { fullNum } from '../lib/format'

/** Page-number pager for DRF `{count, next, previous}` style lists. */
export function Pager({ page, count, pageSize, onPage }: { page: number; count: number; pageSize: number; onPage: (p: number) => void }) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  if (count === 0) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, count)
  return (
    <div className="row between wrap gap-2" style={{ padding: 'var(--sp-3) var(--sp-4)' }}>
      <span className="caption">{fullNum(from)}–{fullNum(to)} of {fullNum(count)}</span>
      <div className="row gap-2">
        <Button size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Prev</Button>
        <span className="caption num">{page} / {totalPages}</span>
        <Button size="sm" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>Next →</Button>
      </div>
    </div>
  )
}
