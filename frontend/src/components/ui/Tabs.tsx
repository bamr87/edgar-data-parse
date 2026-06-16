import type { ReactNode } from 'react'
import { cx } from '../../lib/format'

export type TabDef = { key: string; label: ReactNode; count?: number; icon?: ReactNode }

export function Tabs({ tabs, value, onChange }: { tabs: TabDef[]; value: string; onChange: (k: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={value === t.key}
          className={cx('tab', value === t.key && 'active')}
          onClick={() => onChange(t.key)}
        >
          {t.icon}
          {t.label}
          {t.count != null && <span className="count">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}
