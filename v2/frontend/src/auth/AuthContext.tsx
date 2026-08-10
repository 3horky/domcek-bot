import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { ApiError, getSession, logout } from '../api/client'
import { AuthContext, type AuthContextValue, type AuthState } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [reloadKey, setReloadKey] = useState(0)
  const [state, setState] = useState<AuthState>({ status: 'loading', session: null, error: null })

  useEffect(() => {
    const controller = new AbortController()
    void getSession(controller.signal)
      .then((session) => {
        if (!controller.signal.aborted) {
          setState({ status: 'authenticated', session, error: null })
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        if (error instanceof ApiError && error.status === 401) {
          setState({ status: 'anonymous', session: null, error: null })
          return
        }
        setState({
          status: 'error',
          session: null,
          error:
            error instanceof ApiError ? error : new ApiError('Neznáma chyba prihlásenia.', 0, null),
        })
      })
    return () => controller.abort()
  }, [reloadKey])

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      retry: () => {
        setState({ status: 'loading', session: null, error: null })
        setReloadKey((current) => current + 1)
      },
      signOut: async () => {
        await logout()
        setState({ status: 'anonymous', session: null, error: null })
      },
    }),
    [state],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
