import { useState } from 'react'

const STORAGE_KEY = 'secuscan:preferred-export-format'

function readPreferredFormat(): string | null {
    try {
        return localStorage.getItem(STORAGE_KEY)
    } catch {
        // Private mode / blocked storage — do not crash render.
        return null
    }
}

export function usePreferredExportFormat() {
    const [preferred, setPreferred] = useState<string | null>(readPreferredFormat)

    function savePreference(format: string) {
        try {
            localStorage.setItem(STORAGE_KEY, format)
        } catch {
            // Ignore write failures (quota / private mode); still update React state.
        }
        setPreferred(format)
    }

    return { preferred, savePreference }
}
