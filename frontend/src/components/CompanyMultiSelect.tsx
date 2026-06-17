/** Search + multi-select companies (chips). Used to build comparison sets. */
import { useEffect, useRef, useState } from 'react'
import { useCompanies } from '../lib/queries'
import { useDebounce } from '../lib/useDebounce'
import { cik10, cx } from '../lib/format'
import { IconPlus, IconSearch } from './ui/icons'
import { Spinner } from './ui/states'

export type PickedCompany = { id: number; name: string; ticker: string | null; cik: string }

export function CompanyMultiSelect({ selected, onChange, placeholder = 'Add a company…' }: {
  selected: PickedCompany[]
  onChange: (next: PickedCompany[]) => void
  placeholder?: string
}) {
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const debounced = useDebounce(q, 250)
  const ref = useRef<HTMLDivElement>(null)
  const query = useCompanies(debounced.trim() ? { search: debounced.trim() } : { search: '' })
  const chosen = new Set(selected.map((s) => s.id))
  const results = (debounced.trim() ? query.data?.results ?? [] : []).filter((c) => !chosen.has(c.id)).slice(0, 8)

  useEffect(() => {
    const onClick = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  function add(c: { id: number; name: string; ticker: string | null; cik: string }) {
    onChange([...selected, { id: c.id, name: c.name, ticker: c.ticker, cik: cik10(c.cik) }])
    setQ('')
    setOpen(false)
  }

  return (
    <div className="col gap-2">
      {selected.length > 0 && (
        <div className="row gap-2 wrap">
          {selected.map((c) => (
            <span key={c.id} className="badge badge-accent" style={{ gap: 6 }}>
              {c.ticker || c.name.slice(0, 16)}
              <button className="link-btn" style={{ color: 'inherit', lineHeight: 1 }} onClick={() => onChange(selected.filter((x) => x.id !== c.id))} aria-label={`Remove ${c.name}`}>✕</button>
            </span>
          ))}
        </div>
      )}
      <div className="combo" ref={ref}>
        <div className="search-box">
          <IconSearch width={16} height={16} className="ico" />
          <input className="input" value={q} placeholder={placeholder} onChange={(e) => { setQ(e.target.value); setOpen(true) }} onFocus={() => setOpen(true)} />
        </div>
        {open && debounced.trim().length >= 1 && (
          <div className="combo-panel">
            {query.isPending ? (
              <div className="combo-empty"><Spinner /> Searching…</div>
            ) : results.length === 0 ? (
              <div className="combo-empty">No more matches for “{debounced}”.</div>
            ) : (
              results.map((c) => (
                <div key={c.id} className={cx('combo-item')} onClick={() => add(c)}>
                  <IconPlus width={14} height={14} />
                  <div className="grow">
                    <div className="truncate" style={{ fontWeight: 600 }}>{c.name}</div>
                    <div className="caption">{c.ticker ? `${c.ticker} · ` : ''}CIK {c.cik}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
