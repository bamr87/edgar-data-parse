/** Generic, client-sortable table. Columns declare how to render + sort each cell. */
import { useMemo, useState, type ReactNode } from 'react'
import { cx } from '../../lib/format'

export type Column<T> = {
  key: string
  header: ReactNode
  render: (row: T) => ReactNode
  align?: 'left' | 'right'
  sortable?: boolean
  sortValue?: (row: T) => number | string
  width?: number | string
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  onRowHover,
  compact,
  initialSort,
  className,
}: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T, i: number) => string | number
  onRowClick?: (row: T) => void
  onRowHover?: (row: T) => void
  compact?: boolean
  initialSort?: { key: string; dir: 'asc' | 'desc' }
  className?: string
}) {
  const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(initialSort ?? null)

  const sorted = useMemo(() => {
    if (!sort) return rows
    const col = columns.find((c) => c.key === sort.key)
    if (!col?.sortValue) return rows
    const dir = sort.dir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const va = col.sortValue!(a)
      const vb = col.sortValue!(b)
      if (va < vb) return -1 * dir
      if (va > vb) return 1 * dir
      return 0
    })
  }, [rows, sort, columns])

  function toggleSort(key: string) {
    setSort((s) => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }))
  }

  return (
    <div className="table-wrap">
      <table className={cx('tbl', compact && 'tbl-compact', className)}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={cx(c.sortable && 'sortable', c.align === 'right' && 'td-num')}
                style={c.width ? { width: c.width } : undefined}
                onClick={c.sortable ? () => toggleSort(c.key) : undefined}
              >
                {c.header}
                {sort?.key === c.key && <span className="subtle"> {sort.dir === 'asc' ? '▲' : '▼'}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={rowKey(row, i)} className={cx(onRowClick && 'clickable')} onClick={onRowClick ? () => onRowClick(row) : undefined} onMouseEnter={onRowHover ? () => onRowHover(row) : undefined}>
              {columns.map((c) => (
                <td key={c.key} className={cx(c.align === 'right' && 'td-num')}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
