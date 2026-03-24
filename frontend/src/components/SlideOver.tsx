import React, { useEffect } from 'react'

interface SlideOverProps {
    isOpen: boolean
    onClose: () => void
    children: React.ReactNode
}

export default function SlideOver({ isOpen, onClose, children }: SlideOverProps) {
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                onClose()
            }
        }

        document.addEventListener('keydown', handleEscape)
        return () => document.removeEventListener('keydown', handleEscape)
    }, [isOpen, onClose])

    if (!isOpen) return null

    return (
        <>
            <div className="slideover-backdrop" onClick={onClose} />
            <div className="slideover">
                <div className="slideover-content">
                    {children}
                </div>
            </div>
        </>
    )
}
