import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../services/api'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [plugins, setPlugins] = useState([])
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadInitialData()
  }, [])

  async function loadInitialData() {
    try {
      setLoading(true)
      const [pluginsData, settingsData] = await Promise.all([
        api.getPlugins(),
        api.getSettings(),
      ])
      setPlugins(pluginsData.plugins || [])
      setSettings(settingsData)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const value = {
    plugins,
    settings,
    loading,
    error,
    reload: loadInitialData,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}
