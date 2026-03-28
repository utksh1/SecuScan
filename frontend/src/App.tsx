import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import Assets from './pages/Assets'
import Scanner from './pages/Scanner'
import ToolConfig from './pages/ToolConfig'
import Findings from './pages/Findings'
import AttackSurface from './pages/AttackSurface'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import History from './pages/History'
import TaskDetails from './pages/TaskDetails'
import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider, ToastContainer } from './components/ToastContext'
import { I18nProvider } from './components/I18nContext'
import { routes } from './routes'

export function AppRoutes() {
  return (
    <Routes>
      <Route path={routes.dashboard} element={<Dashboard />} />
      <Route path={routes.assets} element={<Assets />} />
      <Route path={routes.scans} element={<Scanner />} />
      <Route path={routes.scanTool} element={<ToolConfig />} />
      <Route path={routes.findings} element={<Findings />} />
      <Route path={routes.attackSurface} element={<AttackSurface />} />
      <Route path={routes.reports} element={<Reports />} />
      <Route path={routes.settings} element={<Settings />} />
      <Route path={routes.history} element={<History />} />
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
          <ToastContainer />
        </ToastProvider>
      </I18nProvider>
    </ThemeProvider>
  )
}
