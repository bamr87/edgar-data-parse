/** Small presentational primitives composed from the design-system CSS. */
import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { cx } from '../../lib/format'

// ---- Card ----
export function Card({ className, children, hover }: { className?: string; children: ReactNode; hover?: boolean }) {
  return <div className={cx('card', hover && 'card-hover', className)}>{children}</div>
}

export function CardHeader({ title, sub, actions, icon }: { title: ReactNode; sub?: ReactNode; actions?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="card-head">
      <div className="card-title-row">
        {icon}
        <div>
          <h3>{title}</h3>
          {sub && <div className="caption">{sub}</div>}
        </div>
      </div>
      {actions && <div className="row gap-2">{actions}</div>}
    </div>
  )
}

// ---- Stat tile ----
export function Stat({ label, value, sub, accent }: { label: ReactNode; value: ReactNode; sub?: ReactNode; accent?: string }) {
  return (
    <div className="stat card">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={accent ? { color: accent } : undefined}>{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

// ---- Badge ----
type Tone = 'default' | 'accent' | 'pos' | 'neg' | 'warn' | 'info'
export function Badge({ children, tone = 'default', dot }: { children: ReactNode; tone?: Tone; dot?: boolean }) {
  const cls = tone === 'default' ? 'badge' : `badge badge-${tone}`
  return (
    <span className={cls}>
      {dot && <span className="dot" />}
      {children}
    </span>
  )
}

// ---- Button ----
type Variant = 'default' | 'primary' | 'ghost' | 'danger'
export function Button({
  variant = 'default',
  size,
  loading,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm'; loading?: boolean }) {
  const cls = cx('btn', variant !== 'default' && `btn-${variant}`, size === 'sm' && 'btn-sm', className)
  return (
    <button className={cls} disabled={rest.disabled || loading} {...rest}>
      {loading && <span className="spinner" style={{ width: 14, height: 14 }} />}
      {children}
    </button>
  )
}

// ---- Form ----
export function Field({ label, hint, children }: { label?: ReactNode; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="field">
      {label && <span className="field-label">{label}</span>}
      {children}
      {hint && <span className="caption">{hint}</span>}
    </div>
  )
}

// ---- Provenance chip ----
export function Provenance({ source, asOf }: { source?: string; asOf?: string | null }) {
  if (!source && !asOf) return null
  return (
    <span className="provenance" title="Data provenance">
      <SourceIcon />
      {source}
      {asOf ? ` · as of ${asOf.slice(0, 10)}` : ''}
    </span>
  )
}

// ---- Meter bar (for scores) ----
export function Meter({ value, max = 1, min = 0, color }: { value: number; max?: number; min?: number; color?: string }) {
  const pctv = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100))
  return (
    <div className="meter" title={String(value)}>
      <div className="meter-fill" style={{ width: `${pctv}%`, background: color || 'var(--c-accent)' }} />
    </div>
  )
}

// ---- Copy to clipboard ----
export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [done, setDone] = useState(false)
  return (
    <Button
      size="sm"
      variant="ghost"
      onClick={() => {
        navigator.clipboard?.writeText(text).then(() => {
          setDone(true)
          setTimeout(() => setDone(false), 1200)
        })
      }}
    >
      {done ? '✓ Copied' : label}
    </Button>
  )
}

// ---- Segmented control ----
export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: ReactNode }[]; onChange: (v: T) => void }) {
  return (
    <div className="segmented" role="tablist">
      {options.map((o) => (
        <button key={o.value} className={cx(value === o.value && 'active')} onClick={() => onChange(o.value)} role="tab" aria-selected={value === o.value}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

function SourceIcon() {
  return (
    <svg className="ico" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2v20M2 12h20" opacity="0" />
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4l3 2" />
    </svg>
  )
}
