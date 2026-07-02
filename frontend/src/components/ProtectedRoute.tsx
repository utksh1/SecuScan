import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { routes } from '../routes'

/**
 * Gate for routes that require an authenticated user (issue #795).
 *
 * Unauthenticated visitors are redirected to the sign-in page, preserving the
 * route they were trying to reach in navigation state so they can be returned
 * there after signing in. While the persisted session is still being read the
 * gate renders nothing to avoid a redirect flash.
 */
export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to={routes.signIn} state={{ from: location }} replace />
  }

  return <Outlet />
}
