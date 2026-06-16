import type { ReactNode } from 'react'

export function PageHeader({ title, desc, actions, badges }: { title: ReactNode; desc?: ReactNode; actions?: ReactNode; badges?: ReactNode }) {
  return (
    <div className="page-header">
      <div className="row between wrap gap-3">
        <div>
          <div className="page-title">
            <h1>{title}</h1>
            {badges}
          </div>
          {desc && <p className="page-desc">{desc}</p>}
        </div>
        {actions && <div className="row gap-2 wrap">{actions}</div>}
      </div>
    </div>
  )
}
