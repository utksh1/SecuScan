import React, { createContext, useContext, useState } from 'react'

export type CursorStyle = 'default' | 'glow' | 'trail' | 'sparkle' | 'orbit' | 'chess'

interface CursorContextType {
  cursorStyle: CursorStyle
  setCursorStyle: (style: CursorStyle) => void
}

const CursorContext = createContext<CursorContextType | undefined>(undefined)

const STORAGE_KEY = 'secuscan_cursor_style'

export function CursorProvider({ children }: { children: React.ReactNode }) {
  const [cursorStyle, setCursorStyleState] = useState<CursorStyle>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return (saved as CursorStyle) || 'default'
  })

  const setCursorStyle = (style: CursorStyle) => {
    setCursorStyleState(style)
    localStorage.setItem(STORAGE_KEY, style)
  }

  return (
    <CursorContext.Provider value={{ cursorStyle, setCursorStyle }}>
      {children}
    </CursorContext.Provider>
  )
}

export function useCursor(): CursorContextType {
  const context = useContext(CursorContext)
  if (!context) {
    // Return a safe fallback for unit tests rendered outside CursorProvider
    return {
      cursorStyle: 'default',
      setCursorStyle: () => {},
    }
  }
  return context
}