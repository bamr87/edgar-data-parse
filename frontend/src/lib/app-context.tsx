/** Global app state: admin auth token, SEC contact email, and theme. */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { getAuthToken, getSecEmail, setAuthToken, setSecEmail } from './http'

type Theme = 'light' | 'dark' | 'system'

type AppState = {
  token: string
  email: string
  isAdmin: boolean
  theme: Theme
  setToken: (t: string) => void
  setEmail: (e: string) => void
  setTheme: (t: Theme) => void
}

const Ctx = createContext<AppState | null>(null)
const THEME_KEY = 'edgarTheme'

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', theme)
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState(getAuthToken)
  const [email, setEmailState] = useState(getSecEmail)
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      return (localStorage.getItem(THEME_KEY) as Theme) || 'system'
    } catch {
      return 'system'
    }
  })

  useEffect(() => applyTheme(theme), [theme])

  const setToken = useCallback((t: string) => {
    const v = t.trim()
    setAuthToken(v || null)
    setTokenState(v)
  }, [])

  const setEmail = useCallback((e: string) => {
    const v = e.trim()
    setSecEmail(v || null)
    setEmailState(v)
  }, [])

  const setTheme = useCallback((t: Theme) => {
    try {
      localStorage.setItem(THEME_KEY, t)
    } catch {
      /* private mode */
    }
    setThemeState(t)
  }, [])

  const value = useMemo<AppState>(
    () => ({ token, email, isAdmin: !!token, theme, setToken, setEmail, setTheme }),
    [token, email, theme, setToken, setEmail, setTheme],
  )

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useApp(): AppState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
