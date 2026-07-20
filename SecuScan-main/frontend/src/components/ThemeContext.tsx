import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react'

type Theme = 'dark' | 'light'

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  isSystemControlled: boolean
  resetToSystem: () => void
}

const STORAGE_KEY = 'secuscan-theme'

function getSystemTheme(): Theme {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  }
  return 'dark'
}

function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark')
    root.classList.remove('theme-light')
  } else {
    root.classList.remove('dark')
    root.classList.add('theme-light')
  }
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Priority 1: manual localStorage override
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
    // Priority 2: OS preference
    return getSystemTheme()
  })

  const [isSystemControlled, setIsSystemControlled] = useState<boolean>(
    () => !localStorage.getItem(STORAGE_KEY)
  )

  // Apply theme class on every change
  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // Listen for OS preference changes — only auto-follow if no manual override
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem(STORAGE_KEY)) {
        const next: Theme = e.matches ? 'dark' : 'light'
        setThemeState(next)
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const setTheme = useCallback((next: Theme) => {
    localStorage.setItem(STORAGE_KEY, next)
    setIsSystemControlled(false)
    setThemeState(next)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }, [theme, setTheme])

  const resetToSystem = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setIsSystemControlled(true)
    const sys = getSystemTheme()
    setThemeState(sys)
  }, [])

  return (
    <ThemeContext.Provider
      value={{ theme, setTheme, toggleTheme, isSystemControlled, resetToSystem }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within a ThemeProvider')
  return context
}
