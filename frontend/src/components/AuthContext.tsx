import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from 'react'
import { checkAuthSession, logoutSession, AUTH_REQUIRED_EVENT } from '../api'


interface AuthContextValue {
  isAuthenticated: boolean
  loading: boolean
  markAuthenticated: () => void
  signOut: () => Promise<void>
}

const defaultValue: AuthContextValue = {
  isAuthenticated: false,
  loading: false,
  markAuthenticated: () => {},
  signOut: async () => {},
}

const AuthContext = createContext<AuthContextValue>(defaultValue)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    checkAuthSession().then((authenticated) => {
      if (!cancelled) {
        setIsAuthenticated(authenticated)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    function onAuthRequired() {
      setIsAuthenticated(false)
    }
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired)
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired)
  }, [])

  const markAuthenticated = useCallback(() => {
    setIsAuthenticated(true)
  }, [])

  const signOut = useCallback(async () => {
    await logoutSession()
    setIsAuthenticated(false)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ isAuthenticated, loading, markAuthenticated, signOut }),
    [isAuthenticated, loading, markAuthenticated, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext)
}
