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
import CompareTasks from './pages/CompareTasks'
import Login from './pages/Login'
import { ThemeProvider } from './components/ThemeContext'
import { ToastProvider, ToastContainer } from './components/ToastContext'

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <Router>
          <AppShell>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/login" element={<Login />} />
              <Route path="/assets" element={<Assets />} />
              <Route path="/scans" element={<Scanner />} />
              <Route path="/scans/:toolId" element={<ToolConfig />} />
              <Route path="/findings" element={<Findings />} />
              <Route path="/attack-surface" element={<AttackSurface />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/history" element={<History />} />
              <Route path="/task/:taskId" element={<TaskDetails />} />
              <Route path="/compare" element={<CompareTasks />} />
            </Routes>
          </AppShell>
        </Router>
        <ToastContainer />
      </ToastProvider>
    </ThemeProvider>
  )
}
