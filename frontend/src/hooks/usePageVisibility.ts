import { useEffect, useState } from 'react'

export function usePageVisibility(): boolean {
    const [isVisible, setIsVisible] = useState<boolean>(
        () => document.visibilityState === 'visible'
    )

    useEffect(() => {
        const handleChange = () => {
            setIsVisible(document.visibilityState === 'visible')
        }

        document.addEventListener('visibilitychange', handleChange)

        return () => {
            document.removeEventListener('visibilitychange', handleChange)
        }
    }, [])

    return isVisible
}