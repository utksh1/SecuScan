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
function isSafeInternalPath(path: string): boolean {
  if (!path.startsWith('/')) {
    return false
  }
  // Prevent protocol-relative URLs like //evil.com
  if (path.startsWith('//')) {
    return false
  }
  // Prevent backslash protocol-relative bypasses or Windows share paths like /\evil.com
  if (path.startsWith('/\\')) {
    return false
  }
  // Ensure no protocols/schemes (e.g. http://, https://, javascript:) are in the pathname
  if (/^[a-z0-9+.-]+:/i.test(path.trim())) {
    return false
  }
  return true
}

export default function SignIn() {
  const { isAuthenticated, loading, markAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: { pathname?: string } } }
  
  const rawFrom = location.state?.from?.pathname
  const from = rawFrom && isSafeInternalPath(rawFrom) ? rawFrom : routes.dashboard

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
