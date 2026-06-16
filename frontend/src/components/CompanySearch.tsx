/** Global company search combobox — searches the warehouse and navigates to the
 *  Company-360 page. Used in the top bar and on the dashboard. */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCompanies } from '../lib/queries'
import { useDebounce } from '../lib/useDebounce'
import { cx } from '../lib/format'
import { IconSearch } from './ui/icons'
import { Spinner } from './ui/states'

export function CompanySearch({ placeholder = 'Search companies by name, ticker, or CIK…', autoFocus }: { placeholder?: string; autoFocus?: boolean }) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const debounced = useDebounce(q, 250)
  const navigate = useNavigate()
  const ref = useRef<HTMLDivElement>(null)

  const query = useCompanies(debounced.trim().length >= 1 ? { search: debounced.trim() } : { search: '' })
  const results = (debounced.trim() ? query.data?.results ?? [] : []).slice(0, 8)

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  function go(id: number) {
    setOpen(false)
    setQ('')
    navigate(`/companies/${id}`)
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter' && results[active]) { go(results[active].id) }
    else if (e.key === 'Escape') { setOpen(false) }
  }

  return (
    <div className="combo grow" ref={ref}>
      <div className="search-box">
        <IconSearch width={16} height={16} className="ico" />
        <input
          className="input"
          value={q}
          autoFocus={autoFocus}
          placeholder={placeholder}
          onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(0) }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKey}
          aria-label="Search companies"
        />
      </div>
      {open && debounced.trim().length >= 1 && (
        <div className="combo-panel">
          {query.isPending ? (
            <div className="combo-empty"><Spinner /> Searching…</div>
          ) : results.length === 0 ? (
            <div className="combo-empty">No companies in the warehouse match “{debounced}”. Add one from Settings → Add company.</div>
          ) : (
            results.map((c, i) => (
              <div key={c.id} className={cx('combo-item', i === active && 'active')} onMouseEnter={() => setActive(i)} onClick={() => go(c.id)}>
                <div className="brand-mark" style={{ width: 28, height: 28, fontSize: 12, background: 'var(--c-surface-3)', color: 'var(--c-text-muted)' }}>
                  {(c.ticker || c.name).slice(0, 2).toUpperCase()}
                </div>
                <div className="grow">
                  <div className="truncate" style={{ fontWeight: 600 }}>{c.name}</div>
                  <div className="caption">{c.ticker ? `${c.ticker} · ` : ''}CIK {c.cik}{c.sic_description ? ` · ${c.sic_description}` : ''}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
