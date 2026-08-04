import { useEffect } from 'react'

/**
 * Global "user pressed Escape" event.
 *
 * `useShortcuts` owns the single window-level keydown listener and re-broadcasts
 * Escape as this event. Popovers and dropdowns subscribe via `useEscapeToClose`
 * rather than each registering their own keydown handler, so behaviour stays
 * consistent and the listener count does not grow with the number of overlays
 * on the page.
 */
export const ESCAPE_EVENT = 'secuscan:escape'

/**
 * Close an overlay when Escape is pressed.
 *
 * Only subscribes while `isOpen` is true, so a closed popover does nothing and
 * Escape keeps reaching whatever else is listening.
 *
 * Note that `useShortcuts` blurs the focused field instead of broadcasting when
 * the user is typing in an input, textarea, or contenteditable. Escape inside a
 * panel's own text field therefore leaves the field first and closes the panel
 * on a second press — deliberate, so a stray Escape while typing does not
 * discard what the user was entering.
 *
 * @param isOpen   whether the overlay is currently open
 * @param onClose  called when Escape is pressed while open
 */
export function useEscapeToClose(isOpen: boolean, onClose: () => void) {
    useEffect(() => {
        if (!isOpen) return

        const handleEscape = () => onClose()
        window.addEventListener(ESCAPE_EVENT, handleEscape)
        return () => window.removeEventListener(ESCAPE_EVENT, handleEscape)
    }, [isOpen, onClose])
}
