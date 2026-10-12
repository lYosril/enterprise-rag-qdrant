import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import { authLogout, clearToken, getToken } from '../api/client'

// ─── Types ───────────────────────────────────────────────────────────────────

interface User {
  email: string
}

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string) => void
  logout: () => void
}

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

// ─── Provider ────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // On mount: restore session from sessionStorage token
  useEffect(() => {
    const token = getToken()
    if (token) {
      // We can't easily decode JWT without a library, but we can try to
      // extract the email from the payload for display purposes.
      try {
        const payload = JSON.parse(atob(token.split('.')[1])) as {
          sub?: string
          email?: string
        }
        const email = payload.sub ?? payload.email ?? 'user'
        setUser({ email })
      } catch {
        // Malformed token — clear it
        clearToken()
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback((email: string) => {
    setUser({ email })
  }, [])

  const logout = useCallback(() => {
    authLogout()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
