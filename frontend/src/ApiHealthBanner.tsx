import { useEffect, useState } from 'react'

const base = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') || ''

/**
 * Shown when the browser cannot reach the Django API (proxy down, wrong port, or API not running).
 */
export default function ApiHealthBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const r = await fetch(`${base}/api/v1/health/`, {
          method: 'GET',
          cache: 'no-store',
        })
        if (!cancelled && !r.ok) setVisible(true)
      } catch {
        if (!cancelled) setVisible(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!visible) return null

  return (
    <div className="api-offline-banner" role="alert">
      <div className="api-offline-inner">
        <strong className="api-offline-title">Cannot reach the API</strong>
        <p className="api-offline-body">
          The UI loads, but requests to <code>/api</code> failed. Start Django (e.g.{' '}
          <code>python manage.py runserver</code> from <code>src/</code>), or if the API uses
          another port, set <code>API_PROXY_TARGET</code> in <code>frontend/.env.development.local</code>{' '}
          (see <code>frontend/.env.example</code>). Reload after the API is up.
        </p>
        <button type="button" className="btn api-offline-dismiss" onClick={() => setVisible(false)}>
          Dismiss
        </button>
      </div>
    </div>
  )
}
