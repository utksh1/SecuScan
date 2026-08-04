import React, { useEffect, useState } from 'react'
import { useCursor } from '../context/CursorContext'

export const CustomCursor: React.FC = () => {
  const { cursorStyle } = useCursor()
  const [position, setPosition] = useState({ x: -100, y: -100 })
  const [isPointer, setIsPointer] = useState(false)

  useEffect(() => {
    if (cursorStyle === 'default') return

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY })

      const target = e.target as HTMLElement | null
      if (target) {
        const computedCursor = window.getComputedStyle(target).cursor
        setIsPointer(
          computedCursor === 'pointer' ||
            target.tagName === 'BUTTON' ||
            target.tagName === 'A' ||
            target.closest('button') !== null ||
            target.closest('a') !== null
        )
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [cursorStyle])

  if (cursorStyle === 'default') return null

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[9999] overflow-hidden"
      aria-hidden="true"
    >
      <div
        className={`fixed top-0 left-0 -translate-x-1/2 -translate-y-1/2 transition-transform duration-75 ease-out ${
          isPointer ? 'scale-125' : 'scale-100'
        }`}
        style={{
          transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        }}
      >
        {cursorStyle === 'glow' && (
          <div className="h-8 w-8 rounded-full bg-amber-400/40 blur-md shadow-[0_0_15px_rgba(251,191,36,0.8)]" />
        )}

        {cursorStyle === 'trail' && (
          <div className="h-6 w-6 rounded-full border-2 border-rag-red bg-rag-red/20 backdrop-blur-sm" />
        )}

        {cursorStyle === 'sparkle' && (
          <div className="relative flex h-6 w-6 items-center justify-center text-amber-400 animate-pulse text-sm">
            ✨
          </div>
        )}

        {cursorStyle === 'orbit' && (
          <div className="relative h-7 w-7 animate-spin rounded-full border-2 border-dashed border-silver-bright" />
        )}

        {cursorStyle === 'chess' && (
          <div className="flex h-7 w-7 items-center justify-center text-lg drop-shadow-[0_2px_4px_rgba(0,0,0,0.6)]">
            ♟️
          </div>
        )}
      </div>
    </div>
  )
}
