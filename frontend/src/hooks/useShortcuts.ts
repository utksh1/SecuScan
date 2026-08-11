import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { routes } from '../routes'
import { ESCAPE_EVENT } from './useEscapeToClose'


export function useShortcuts(onToggleSidebar?: () => void) {
    const navigate = useNavigate()

    useEffect(() => {
        let lastChar = ''

        const handleKeyDown = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
                if (e.key === 'Escape') {
                    target.blur()
                }
                return
            }

            if (e.key === 'Escape') {
                window.dispatchEvent(new CustomEvent(ESCAPE_EVENT))
                return
            }

            const key = e.key.toLowerCase()

            if (lastChar === 'g') {
                switch (key) {
                    case 'd': navigate(routes.dashboard); break
                    case 's': navigate(routes.scans); break
                    case 'f': navigate(routes.findings); break
                    case 'r': navigate(routes.reports); break
                    case 't': navigate(routes.settings); break
                    case 'b': {
                        onToggleSidebar?.()
                        break
                    }
                }
                lastChar = ''
            } else if (key === 'g') {
                lastChar = 'g'
                setTimeout(() => { lastChar = '' }, 1000)
            } else {
                lastChar = ''
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [navigate, onToggleSidebar])
}
