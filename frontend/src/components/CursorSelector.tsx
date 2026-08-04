import React, { useState, useRef, useEffect } from 'react'
import { useCursor, CursorStyle } from '../context/CursorContext'

const OPTIONS: { label: string; value: CursorStyle; icon: string }[] = [
  { label: 'Default', value: 'default', icon: 'near_me' },
  { label: 'Glow', value: 'glow', icon: 'light_mode' },
  { label: 'Trail', value: 'trail', icon: 'blur_on' },
  { label: 'Sparkle', value: 'sparkle', icon: 'auto_awesome' },
  { label: 'Orbit', value: 'orbit', icon: 'sync' },
  { label: 'Chess', value: 'chess', icon: 'sports_esports' },
]

export const CursorSelector: React.FC = () => {
  const { cursorStyle, setCursorStyle } = useCursor()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const activeOption = OPTIONS.find((opt) => opt.value === cursorStyle) || OPTIONS[0]

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="h-9 px-3 flex items-center gap-2 rounded border border-accent-silver/20 bg-charcoal-dark text-silver-bright hover:bg-charcoal-light transition-colors text-xs font-medium"
        aria-label="Select cursor style"
        aria-expanded={isOpen}
      >
        <span className="material-symbols-outlined text-[18px]">
          {activeOption.icon}
        </span>
        <span className="hidden sm:inline">{activeOption.label}</span>
        <span className="material-symbols-outlined text-[16px] transition-transform duration-200">
          {isOpen ? 'expand_less' : 'expand_more'}
        </span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 origin-top-right rounded border border-accent-silver/20 bg-[var(--bg-secondary)] py-1 shadow-lg z-[70]">
          {OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setCursorStyle(opt.value)
                setIsOpen(false)
              }}
              className={`flex w-full items-center gap-2 px-3 py-2 text-xs transition-colors ${
                cursorStyle === opt.value
                  ? 'bg-rag-red/10 text-silver-bright font-bold'
                  : 'text-silver/80 hover:bg-charcoal-light/50 hover:text-silver-bright'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">
                {opt.icon}
              </span>
              <span>{opt.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
