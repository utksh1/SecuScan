import React, { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import ApiKeySetupScreen from '../components/ApiKeySetupScreen'
import { useAuth } from '../components/AuthContext'
import { routes } from '../routes'

/**
 * Sign In route (issue #795).
 *
 * SecuScan authenticates by API key, which the backend exchanges for an HttpOnly
 * session cookie. Rather than invent a second credential UI, this route reuses
 * the existing, real `ApiKeySetupScreen` (it calls `authenticateWithApiKey()` →
 * POST /api/v1/auth/session). On success we mark the session authenticated and
 * return the operator to the route they were sent here from (or the dashboard).
 */
export default function SignIn() {
  const { isAuthenticated, loading, markAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: { pathname?: string } } }
  const from = location.state?.from?.pathname || routes.dashboard

  // If a valid session already exists, don't show the key prompt.
  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [loading, isAuthenticated, from, navigate])

  return (
    <ApiKeySetupScreen
      onSaved={() => {
        markAuthenticated()
        navigate(from, { replace: true })
      }}
    />
  )
}
