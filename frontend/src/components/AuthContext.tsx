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

/**
 * Authentication state for protected features (issue #795).
 *
 * This is a thin wrapper over SecuScan's real, backend-backed session auth — it
 * holds NO credentials of its own. Session state is derived from the HttpOnly
 * cookie via `checkAuthSession()` (GET /api/v1/auth/session/check); the cookie is
 * established by `authenticateWithApiKey()` (POST /api/v1/auth/session) and torn
 * down by `logoutSession()` (POST /api/v1/auth/session/logout). A 401 from any
 * API call dispatches AUTH_REQUIRED_EVENT, which drops us back to unauthenticated
 * so the route guard can send the operator to sign in again.
 */
interface AuthContextValue {
  /** True only when the backend confirms a valid session cookie. */
  isAuthenticated: boolean
  /** True while the initial session check is in flight. */
  loading: boolean
  /**
   * Flip to authenticated after a successful `authenticateWithApiKey()` call
   * (the backend has already validated the key and set the cookie). This is not
   * a self-asserted flag — it only follows a server-verified sign-in.
   */
  markAuthenticated: () => void
  /** Clear the backend session (logout endpoint) and drop to unauthenticated. */
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

  // Derive the initial session state from the backend cookie.
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

  // A 401 anywhere invalidates the session.
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
