import React, { useState } from 'react'
import { assignFinding } from '../api'
import { useToast } from './ToastContext'

interface AssignmentControlProps {
  findingId: string
  assignedTo: string | null
  assignedBy: string | null
  onAssignmentChange: (assignedTo: string | null) => void
}

export default function AssignmentControl({
  findingId,
  assignedTo,
  assignedBy,
  onAssignmentChange,
}: AssignmentControlProps) {
  const [editing, setEditing] = useState(false)
  const [assignInput, setAssignInput] = useState(assignedTo || '')
  const [saving, setSaving] = useState(false)
  const { showToast } = useToast()

  const handleSaveAssignment = async () => {
    if (!assignInput.trim()) {
      showToast('Please enter a user ID', 'error')
      return
    }

    setSaving(true)
    try {
      await assignFinding(findingId, assignInput)
      onAssignmentChange(assignInput)
      setEditing(false)
      showToast('Finding assigned successfully', 'success')
    } catch (error) {
      showToast('Failed to assign finding', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mb-4 rounded border border-silver-bright/20 bg-charcoal-dark/50 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold uppercase tracking-widest text-silver-bright">Assigned To</h3>
        {assignedTo && !editing && (
          <button
            onClick={() => {
              setEditing(true)
              setAssignInput(assignedTo || '')
            }}
            className="text-xs font-mono text-rag-blue hover:text-rag-blue/80 transition-colors"
          >
            Edit
          </button>
        )}
      </div>

      <div className="mt-3">
        {!editing ? (
          <div>
            {assignedTo ? (
              <div>
                <div className="rounded bg-charcoal px-3 py-2 text-sm font-mono text-silver-bright">
                  {assignedTo}
                </div>
                {assignedBy && (
                  <div className="mt-2 text-xs text-silver/60">
                    Assigned by: <span className="font-mono">{assignedBy}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded bg-charcoal/40 px-3 py-2 text-xs text-silver/60 italic">
                No assignment yet
              </div>
            )}
            <button
              onClick={() => setEditing(true)}
              className="mt-3 rounded border border-rag-blue bg-rag-blue/10 px-3 py-1 text-xs font-bold text-rag-blue hover:bg-rag-blue/20 transition-all"
            >
              {assignedTo ? 'Reassign' : 'Assign To Team Member'}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <input
              type="text"
              value={assignInput}
              onChange={(e) => setAssignInput(e.target.value)}
              placeholder="e.g., user:alice or user:bob"
              className="w-full rounded border border-rag-blue/50 bg-charcoal px-3 py-2 text-xs font-mono text-silver-bright placeholder-silver/40 focus:border-rag-blue focus:outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setEditing(false)
                  setAssignInput(assignedTo || '')
                }}
                className="rounded border border-silver-bright/20 bg-charcoal px-2 py-1 text-xs font-bold text-silver-bright hover:border-silver-bright/50 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAssignment}
                disabled={saving}
                className="rounded bg-rag-blue px-3 py-1 text-xs font-bold text-black hover:bg-rag-blue/90 disabled:opacity-50 transition-all"
              >
                {saving ? 'Assigning...' : 'Assign'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
