/** Loading / empty / error states + a <Query> boundary that maps a TanStack
 *  Query result to the right state, so pages stay declarative. */
import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { ApiError } from '../../lib/http'

export function Spinner({ lg }: { lg?: boolean }) {
  return <span className={lg ? 'spinner spinner-lg' : 'spinner'} aria-label="Loading" />
}

export function Loading({ label = 'Loading…', pad }: { label?: string; pad?: boolean }) {
  return (
    <div className="state" style={pad ? undefined : { padding: 'var(--sp-5)' }}>
      <Spinner lg />
      <div className="muted">{label}</div>
    </div>
  )
}

export function EmptyState({ title, message, icon, action }: { title: string; message?: ReactNode; icon?: ReactNode; action?: ReactNode }) {
  return (
    <div className="state">
      {icon}
      <div className="state-title">{title}</div>
      {message && <div className="muted" style={{ maxWidth: '46ch' }}>{message}</div>}
      {action}
    </div>
  )
}

export function ErrorState({ error, action }: { error: unknown; action?: ReactNode }) {
  const e = error as ApiError | Error
  const status = e instanceof ApiError ? e.status : undefined
  const auth = e instanceof ApiError && e.isAuth
  return (
    <div className="state">
      <div className="state-title state-error">
        {status ? `Error ${status}` : 'Something went wrong'}
      </div>
      <div className="muted" style={{ maxWidth: '52ch' }}>
        {auth ? 'This action needs an admin token — add one in Settings.' : (e?.message || 'Request failed.')}
      </div>
      {action}
    </div>
  )
}

/**
 * Declarative boundary for a query: shows Loading / ErrorState / EmptyState /
 * children(data). `isEmpty` decides the empty case from the resolved data.
 */
export function Query<T>({
  q,
  children,
  isEmpty,
  empty,
  loadingLabel,
}: {
  q: UseQueryResult<T>
  children: (data: T) => ReactNode
  isEmpty?: (data: T) => boolean
  empty?: ReactNode
  loadingLabel?: string
}) {
  if (q.isPending) return <Loading label={loadingLabel} />
  if (q.isError) return <ErrorState error={q.error} />
  const data = q.data as T
  if (isEmpty?.(data)) return <>{empty ?? <EmptyState title="No data yet" />}</>
  return <>{children(data)}</>
}

export function SkeletonRows({ rows = 4, height = 16 }: { rows?: number; height?: number }) {
  return (
    <div className="col gap-2" style={{ padding: 'var(--sp-3)' }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height, width: `${90 - i * 8}%` }} />
      ))}
    </div>
  )
}
