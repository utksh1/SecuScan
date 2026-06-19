import React, { useState } from 'react'
import { updateFindingVisibility } from '../api'
import { useToast } from './ToastContext'

type Visibility = 'PRIVATE' | 'TEAM' | 'PUBLIC'

interface VisibilityControlProps {
  findingId: string
  currentVisibility: Visibility
  onVisibilityChange: (visibility: Visibility) => void
}

const visibilityConfig: Record<Visibility, { label: string; description: string; icon: string }> = {
  PRIVATE: {
    label: 'Private',
    description: 'Only you can see this finding',
    icon: '🔒',
  },
  TEAM: {
    label: 'Team',
    description: 'Your team can view and collaborate',
    icon: '👥',
  },
  PUBLIC: {
    label: 'Public',
    description: 'Anyone with access can view',
    icon: '🌐',
  },
}

export default function VisibilityControl({
  findingId,
  currentVisibility,
  onVisibilityChange,
}: VisibilityControlProps) {
  const [expanding, setExpanding] = useState(false)
  const [updating, setUpdating] = useState(false)
  const { showToast } = useToast()

  const handleVisibilityChange = async (newVisibility: Visibility) => {
    if (newVisibility === currentVisibility) return

    setUpdating(true)
    try {
      await updateFindingVisibility(findingId, newVisibility)
      onVisibilityChange(newVisibility)
      setExpanding(false)
      showToast(`Visibility changed to ${newVisibility}`, 'success')
    } catch (error) {
      showToast('Failed to update visibility', 'error')
    } finally {
      setUpdating(false)
    }
  }

  const allVisibilities: Visibility[] = ['PRIVATE', 'TEAM', 'PUBLIC']
  const current = visibilityConfig[currentVisibility]

  return (
    <div className="mb-4 rounded border border-silver-bright/20 bg-charcoal-dark/50 p-4">
      <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-silver-bright">Visibility</h3>

      {!expanding ? (
        <button
          onClick={() => setExpanding(true)}
          disabled={updating}
          className="w-full rounded border border-silver-bright/20 bg-charcoal px-3 py-2 text-left text-xs font-medium text-silver-bright hover:border-silver-bright/50 transition-all disabled:opacity-50"
        >
          <div className="flex items-center gap-2">
            <span className="text-sm">{current.icon}</span>
            <div className="flex-1">
              <div className="font-bold">{current.label}</div>
              <div className="text-xs text-silver/60">{current.description}</div>
            </div>
            <span className="text-xs">▼</span>
          </div>
        </button>
      ) : (
        <div className="space-y-2">
          {allVisibilities.map((visibility) => {
            const isActive = visibility === currentVisibility
            const config = visibilityConfig[visibility]

            return (
              <button
                key={visibility}
                onClick={() => handleVisibilityChange(visibility)}
                disabled={updating}
                className={`
                  w-full rounded border px-3 py-2 text-left text-xs transition-all
                  ${isActive
                    ? 'border-rag-blue bg-rag-blue/10'
                    : 'border-silver-bright/20 bg-charcoal hover:border-silver-bright/50'
                  }
                  disabled:opacity-50
                `}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">{config.icon}</span>
                  <div className="flex-1">
                    <div className={`font-bold ${isActive ? 'text-rag-blue' : 'text-silver-bright'}`}>
                      {config.label}
                    </div>
                    <div className="text-xs text-silver/60">{config.description}</div>
                  </div>
                  {isActive && <span className="text-rag-blue">✓</span>}
                </div>
              </button>
            )
          })}
          <button
            onClick={() => setExpanding(false)}
            disabled={updating}
            className="w-full rounded border border-silver-bright/20 bg-charcoal px-3 py-2 text-xs font-bold text-silver-bright hover:border-silver-bright/50 transition-all"
          >
            Close
          </button>
        </div>
      )}
    </div>
  )
}
