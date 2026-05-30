import React from 'react'
import { useTheme } from './ThemeContext'

type Size = 'sm' | 'md'

interface ThemeToggleProps {
  size?: Size
}

export default function ThemeToggle({ size = 'md' }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme()

  const sizeClass = size === 'sm' ? 'w-9 h-9' : 'w-10 h-10'
  const iconSize = size === 'sm' ? 'text-lg' : 'text-xl'

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        toggleTheme()
      }}
      className={`
        ${sizeClass}
        flex items-center justify-center
        rounded-lg
        bg-slate-200 dark:bg-slate-700
        hover:bg-slate-300 dark:hover:bg-slate-600
        transition-colors duration-200
        flex-shrink-0
      `}
      aria-label={`Toggle to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      <span className={`material-symbols-outlined ${iconSize}`}>
        {theme === 'dark' ? 'light_mode' : 'dark_mode'}
      </span>
    </button>
  )
}
