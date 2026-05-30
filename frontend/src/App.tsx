import React from 'react'
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom'

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

import ErrorBoundary from './components/error-boundary/ErrorBoundary'

import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider } from './components/ToastContext'
import { I18nProvider } from './components/I18nContext'
import { routes } from './routes'

function withErrorBoundary(component: React.ReactNode) {
  return (
    <ErrorBoundary>
      {component}
    </ErrorBoundary>
  )
}

export function AppRoutes() {
  return (
    <Routes>
      <Route
        path={routes.dashboard}
        element={withErrorBoundary(<Dashboard />)}
      />

      <Route
        path={routes.toolkit}
        element={withErrorBoundary(<Toolkit />)}
      />

      <Route
        path={routes.scanTool}
        element={withErrorBoundary(<ToolConfig />)}
      />

      <Route
        path={routes.findings}
        element={withErrorBoundary(<Findings />)}
      />

      <Route
        path={routes.scans}
        element={withErrorBoundary(<Scans />)}
      />

      <Route
        path={routes.reports}
        element={withErrorBoundary(<Reports />)}
      />

      <Route
        path={routes.workflows}
        element={withErrorBoundary(<Workflows />)}
      />

      <Route
        path={routes.settings}
        element={withErrorBoundary(<Settings />)}
      />

      <Route
        path={routes.task}
        element={withErrorBoundary(<TaskDetails />)}
      />

      <Route
        path="*"
        element={<Navigate to={routes.dashboard} replace />}
      />
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