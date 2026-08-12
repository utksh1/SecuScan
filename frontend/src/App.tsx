import React from 'react'
import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom'
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
import SignIn from './pages/SignIn'
import ErrorBoundary from './components/ErrorBoundary'
import ProtectedRoute from './components/ProtectedRoute'

import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider } from './components/ToastContext'
import { AuthProvider } from './components/AuthContext'
import { routes } from './routes'


function ShellLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  )
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path={routes.signIn} element={<SignIn />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<ShellLayout />}>
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
        </Route>
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <ErrorBoundary>
          <AuthProvider>
            <Router>
              <AppRoutes />
            </Router>
          </AuthProvider>
        </ErrorBoundary>
      </ToastProvider>
    </ThemeProvider>
  )
}
