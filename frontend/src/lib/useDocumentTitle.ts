import { useEffect } from 'react'

const BASE = 'Fredgar AI'

/** Sets document.title to "<title> · Fredgar AI" while the component is mounted,
 *  restoring whatever title was there before on unmount. Capturing the previous
 *  value (rather than always resetting to BASE) avoids clobbering a title set by
 *  another mounted setter and prevents flicker under StrictMode double-invoke. */
export function useDocumentTitle(title: string | null | undefined) {
  useEffect(() => {
    const prev = document.title
    document.title = title ? `${title} · ${BASE}` : BASE
    return () => {
      document.title = prev
    }
  }, [title])
}
