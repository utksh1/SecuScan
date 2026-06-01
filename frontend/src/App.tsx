import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import Toolkit from './pages/Toolkit'
import ToolConfig from './pages/ToolConfig'
import Findings from './pages/Findings'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import Scans from './pages/Scans'
import TaskDetails from './pages/TaskDetails'
import Workflows from './pages/Workflows'
import AuditLog from './pages/AuditLog'

import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider, ToastContainer } from './components/ToastContext'
import { I18nProvider } from './components/I18nContext'
import { routes } from './routes'

export function AppRoutes() {
  return (
    <Routes>
      <Route path={routes.dashboard} element={<Dashboard />} />
      <Route path={routes.toolkit} element={<Toolkit />} />
      <Route path={routes.scanTool} element={<ToolConfig />} />
      <Route path={routes.findings} element={<Findings />} />
      <Route path={routes.scans} element={<Scans />} />
      <Route path={routes.reports} element={<Reports />} />
      <Route path={routes.workflows} element={<Workflows />} />
      <Route path={routes.audit} element={<AuditLog />} />
      <Route path={routes.settings} element={<Settings />} />
      <Route path={routes.task} element={<TaskDetails />} />

      <Route path="*" element={<Navigate to={routes.dashboard} replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <ToastProvider>
          <Router>
            <AppShell>
              <AppRoutes />
            </AppShell>
          </Router>
        </ToastProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
