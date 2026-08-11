import React, { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import ApiKeySetupScreen from '../components/ApiKeySetupScreen'
import { useAuth } from '../components/AuthContext'
import { routes } from '../routes'


export default function SignIn() {
  const { isAuthenticated, loading, markAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: { pathname?: string } } }
  const from = location.state?.from?.pathname || routes.dashboard

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
