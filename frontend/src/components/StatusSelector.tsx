import React, { useState } from 'react'
import { updateFindingStatus } from '../api'
import { useToast } from './ToastContext'

type FindingStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED'

interface StatusSelectorProps {
  findingId: string
  currentStatus: FindingStatus
  onStatusChange: (status: FindingStatus) => void
}

const statusConfig: Record<FindingStatus, { label: string; color: string; bgColor: string }> = {
  OPEN: { label: 'Open', color: 'text-rag-red', bgColor: 'bg-rag-red/20' },
  IN_PROGRESS: { label: 'In Progress', color: 'text-rag-amber', bgColor: 'bg-rag-amber/20' },
  RESOLVED: { label: 'Resolved', color: 'text-rag-green', bgColor: 'bg-rag-green/20' },
}

export default function StatusSelector({
  findingId,
  currentStatus,
  onStatusChange,
}: StatusSelectorProps) {
  const [updating, setUpdating] = useState(false)
  const { showToast } = useToast()

  const handleStatusChange = async (newStatus: FindingStatus) => {
    if (newStatus === currentStatus) return

    setUpdating(true)
    try {
      await updateFindingStatus(findingId, newStatus)
      onStatusChange(newStatus)
      showToast(`Status updated to ${newStatus}`, 'success')
    } catch (error) {
      showToast('Failed to update status', 'error')
    } finally {
      setUpdating(false)
    }
  }

  const allStatuses: FindingStatus[] = ['OPEN', 'IN_PROGRESS', 'RESOLVED']

  return (
    <div className="mb-4 rounded border border-silver-bright/20 bg-charcoal-dark/50 p-4">
      <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-silver-bright">Status</h3>

      <div className="space-y-2">
        {allStatuses.map((status) => {
          const isActive = status === currentStatus
          const config = statusConfig[status]

          return (
            <button
              key={status}
              onClick={() => handleStatusChange(status)}
              disabled={updating}
              className={`
                w-full rounded px-3 py-2 text-xs font-bold uppercase tracking-widest transition-all
                ${isActive ?
                  `${config.bgColor} ${config.color} border-2 border-current` :
                  'border border-silver-bright/20 bg-charcoal text-silver-bright hover:border-silver-bright/50'
                }
                disabled:opacity-50
              `}
            >
              {config.label}
              {isActive && ' ✓'}
            </button>
          )
        })}
      </div>

      {updating && (
        <div className="mt-3 text-center text-xs text-silver/60">Updating...</div>
      )}
    </div>
  )
}
