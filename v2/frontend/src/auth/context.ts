import { createContext, useContext } from 'react'

import type { ApiError, SessionResponse } from '../api/client'

export type AuthState =
  | { status: 'loading'; session: null; error: null }
  | { status: 'anonymous'; session: null; error: null }
  | { status: 'error'; session: null; error: ApiError }
  | { status: 'authenticated'; session: SessionResponse; error: null }

export type AuthContextValue = AuthState & {
  sessionExpired: boolean
  retry: () => void
  refreshSession: () => Promise<boolean>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
