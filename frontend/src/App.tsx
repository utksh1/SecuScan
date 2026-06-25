import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import Toolkit from './pages/Toolkit'
import ToolConfig from './pages/ToolConfig'
import Findings from './pages/Findings'
import Reports from './pages/Reports'
import ReportCompare from './pages/ReportCompare'
import Settings from './pages/Settings'
import Scans from './pages/Scans'
import TaskDetails from './pages/TaskDetails'
import Workflows from './pages/Workflows'
import NotFound from './pages/NotFound'
import ApiKeySetupScreen from './components/ApiKeySetupScreen'
import ErrorBoundary from './components/ErrorBoundary'

import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider } from './components/ToastContext'
import { I18nProvider } from './components/I18nContext'
import { routes } from './routes'
import { AUTH_REQUIRED_EVENT, checkAuthSession } from './api'

export function AppRoutes() {
  return (
    <Routes>
      <Route path={routes.dashboard} element={<Dashboard />} />
      <Route path={routes.toolkit} element={<Toolkit />} />
      <Route path={routes.scanTool} element={<ToolConfig />} />
      <Route path={routes.findings} element={<Findings />} />
      <Route path={routes.scans} element={<Scans />} />
      <Route path={routes.reports} element={<Reports />} />
      <Route path={routes.reportsCompare} element={<ReportCompare />} />
      <Route path={routes.workflows} element={<Workflows />} />
      <Route path={routes.settings} element={<Settings />} />
      <Route path={routes.task} element={<TaskDetails />} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default function App() {
  const [needsKey, setNeedsKey] = useState(true)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    checkAuthSession().then((authenticated) => {
      setNeedsKey(!authenticated)
      setCheckingSession(false)
    })
  }, [])

  useEffect(() => {
    function onAuthRequired() {
      setNeedsKey(true)
    }
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired)
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired)
  }, [])

  if (checkingSession) {
    return null
  }

  return (
    <ThemeProvider>
      <I18nProvider>
        <ToastProvider>
          <ErrorBoundary>
            {needsKey ? (
              <ApiKeySetupScreen onSaved={() => setNeedsKey(false)} />
            ) : (
              <Router>
                <AppShell>
                  <AppRoutes />
                </AppShell>
              </Router>
            )}
          </ErrorBoundary>
        </ToastProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
