import { useEffect } from 'react'

/** Sets document.title to "<title> · EDGAR Explorer" while the component is mounted. */
export function useDocumentTitle(title: string | null | undefined) {
  useEffect(() => {
    const base = 'EDGAR Explorer'
    document.title = title ? `${title} · ${base}` : base
    return () => {
      document.title = base
    }
  }, [title])
}
