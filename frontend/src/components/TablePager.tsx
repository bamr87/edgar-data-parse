type TablePagerProps = {
  page: number
  totalPages: number
  totalCount?: number
  onPageChange: (page: number) => void
  pageSize?: number
  pageSizeOptions?: number[]
  onPageSizeChange?: (size: number) => void
  disabled?: boolean
}

/**
 * Shared prev/next pagination (and optional page-size select) for data tables.
 */
export default function TablePager({
  page,
  totalPages,
  totalCount,
  onPageChange,
  pageSize,
  pageSizeOptions = [25, 50, 100, 200],
  onPageSizeChange,
  disabled = false,
}: TablePagerProps) {
  const safeTotal = Math.max(1, totalPages)

  return (
    <div className="meta-pager table-pager" role="navigation" aria-label="Table pagination">
      <button
        type="button"
        className="btn"
        disabled={disabled || page <= 1}
        onClick={() => onPageChange(Math.max(1, page - 1))}
      >
        Previous
      </button>
      <span className="muted small table-pager-status">
        Page {page} / {safeTotal}
        {totalCount != null ? ` · ${totalCount.toLocaleString()} total` : ''}
      </span>
      <button
        type="button"
        className="btn"
        disabled={disabled || page >= safeTotal}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
      {onPageSizeChange != null && pageSize != null && (
        <label className="table-pager-size">
          <span className="muted small">Rows per page</span>
          <select
            className="input meta-select"
            value={pageSize}
            disabled={disabled}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            aria-label="Rows per page"
          >
            {pageSizeOptions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}
