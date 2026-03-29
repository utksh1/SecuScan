import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { routes } from '../routes'

/**
 * Global keyboard shortcuts hook for SecuScan.
 * 
 * g + d : Dashboard
 * g + s : Scanners
 * g + h : History
 * g + f : Findings
 * g + a : Assets
 * g + r : Reports
 * g + t : Settings (Tools)
 * Esc   : Close focus/modals
 */
export function useShortcuts() {
    const navigate = useNavigate()

    useEffect(() => {
        let lastChar = ''
        
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ignore if user is typing in an input
            const target = e.target as HTMLElement
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
                if (e.key === 'Escape') {
                    target.blur()
                }
                return
            }

            if (e.key === 'Escape') {
                // Could emit global event to close modals
                return
            }

            const key = e.key.toLowerCase()

            if (lastChar === 'g') {
                switch (key) {
                    case 'd': navigate(routes.dashboard); break
                    case 's': navigate(routes.scans); break
                    case 'h': navigate(routes.scans); break
                    case 'f': navigate(routes.findings); break
                    case 'a': navigate(routes.assets); break
                    case 'r': navigate(routes.reports); break
                    case 't': navigate(routes.settings); break
                }
                lastChar = ''
            } else if (key === 'g') {
                lastChar = 'g'
                // Clear g after 1 second if no matching key follows
                setTimeout(() => { lastChar = '' }, 1000)
            } else {
                lastChar = ''
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [navigate])
}
