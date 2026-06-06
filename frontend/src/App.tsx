import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
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
import ApiKeySetupScreen from './components/ApiKeySetupScreen'

import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider } from './components/ToastContext'
import { I18nProvider } from './components/I18nContext'
import { routes } from './routes'
import { AUTH_REQUIRED_EVENT, getStoredApiKey } from './api'

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

      <Route path="*" element={<Navigate to={routes.dashboard} replace />} />
    </Routes>
  )
}

export default function App() {
  // True when setup is needed: no key stored, or any request got a 401.
  const [needsKey, setNeedsKey] = useState(() => !getStoredApiKey())

  useEffect(() => {
    function onAuthRequired() {
      setNeedsKey(true)
    }
    window.addEventListener(AUTH_REQUIRED_EVENT, onAuthRequired)
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, onAuthRequired)
  }, [])

  return (
    <ThemeProvider>
      <I18nProvider>
        <ToastProvider>
          {needsKey ? (
            // Render ONLY the setup screen — no page routes are mounted, so no
            // API calls can fire and spam 401 failures before the key is saved.
            <ApiKeySetupScreen onSaved={() => setNeedsKey(false)} />
          ) : (
            <Router>
              <AppShell>
                <AppRoutes />
              </AppShell>
            </Router>
          )}
        </ToastProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
