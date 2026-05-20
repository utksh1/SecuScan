import { useState } from 'react'

const STORAGE_KEY = 'secuscan:preferred-export-format'

export function usePreferredExportFormat() {
    const [preferred, setPreferred] = useState<string | null>(
        () => localStorage.getItem(STORAGE_KEY)
    )

    function savePreference(format: string) {
        localStorage.setItem(STORAGE_KEY, format)
        setPreferred(format)
    }

    return { preferred, savePreference }
}
