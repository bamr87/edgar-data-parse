/** Right-side slide-in drawer (for detail panels). Closes on backdrop click / Esc. */
import { useEffect, type ReactNode } from 'react'

export function Drawer({
  open,
  onClose,
  title,
  sub,
  children,
  width = 640,
}: {
  open: boolean
  onClose: () => void
  title?: ReactNode
  sub?: ReactNode
  children: ReactNode
  width?: number
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="drawer-root" role="dialog" aria-modal="true">
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer-panel" style={{ width: Math.min(width, window.innerWidth - 32) }}>
        <div className="drawer-head">
          <div className="grow" style={{ minWidth: 0 }}>
            {title && <h3>{title}</h3>}
            {sub && <div className="caption">{sub}</div>}
          </div>
          <button className="btn btn-icon btn-ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  )
}
