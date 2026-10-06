import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from './api'
import type { User } from './api'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  signup: (data: Parameters<typeof api.signup>[0]) => Promise<User>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore the session from the HttpOnly cookie on page load.
  useEffect(() => {
    api
      .fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const value: AuthState = {
    user,
    loading,
    login: async (email, password) => {
      const u = await api.login(email, password)
      setUser(u)
      return u
    },
    signup: async (data) => {
      const u = await api.signup(data)
      setUser(u)
      return u
    },
    logout: async () => {
      await api.logout()
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
