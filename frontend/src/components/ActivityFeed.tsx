import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getActivity, ActivityRecord } from '../api'
import { useToast } from './ToastContext'

interface ActivityFeedProps {
  findingId: string
  isOpen: boolean
  onToggle: () => void
}

const actionConfig: Record<string, { label: string; icon: string; color: string }> = {
  comment_added: { label: 'Comment Added', icon: '💬', color: 'text-rag-blue' },
  finding_assigned: { label: 'Finding Assigned', icon: '👤', color: 'text-rag-amber' },
  status_changed: { label: 'Status Changed', icon: '📋', color: 'text-rag-amber' },
  visibility_changed: { label: 'Visibility Changed', icon: '👁️', color: 'text-silver-bright' },
}

export default function ActivityFeed({ findingId, isOpen, onToggle }: ActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityRecord[]>([])
  const [loading, setLoading] = useState(false)
  const { showToast } = useToast()

  useEffect(() => {
    if (isOpen) {
      loadActivity()
    }
  }, [isOpen, findingId])

  const loadActivity = async () => {
    setLoading(true)
    try {
      const data = await getActivity(findingId, { limit: 50 })
      setActivities(data.activities || [])
    } catch (error) {
      showToast('Failed to load activity', 'error')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="mb-6 rounded border border-silver-bright/20 bg-charcoal-dark px-4 py-2 text-xs font-bold uppercase tracking-widest text-silver-bright hover:border-silver-bright/50 hover:bg-charcoal/80 transition-all"
      >
        Activity ({activities.length})
      </button>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 rounded border border-silver-bright/20 bg-charcoal-dark/50 p-4 backdrop-blur-sm"
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-widest text-silver-bright">Activity Timeline</h3>
        <button
          onClick={onToggle}
          className="text-xs text-silver-bright/60 hover:text-silver-bright transition-colors"
        >
          ✕
        </button>
      </div>

      <div className="max-h-96 space-y-3 overflow-y-auto">
        {loading ? (
          <div className="text-center text-xs text-silver/60">Loading activity...</div>
        ) : activities.length === 0 ? (
          <div className="text-center text-xs text-silver/60">No activity yet</div>
        ) : (
          activities.map((activity, idx) => {
            const config = actionConfig[activity.action] || {
              label: activity.action,
              icon: '📝',
              color: 'text-silver-bright',
            }

            return (
              <div key={activity.id} className="relative flex gap-3">
                {/* Timeline connector */}
                {idx < activities.length - 1 && (
                  <div className="absolute left-[13px] top-10 bottom-0 w-px bg-silver-bright/10" />
                )}

                {/* Timeline dot */}
                <div className={`mt-1 flex-shrink-0 rounded-full w-7 h-7 flex items-center justify-center bg-charcoal/50 border border-silver-bright/20 text-sm`}>
                  {config.icon}
                </div>

                {/* Activity content */}
                <div className="flex-1 pb-3">
                  <div className="flex items-center justify-between">
                    <div className={`text-xs font-bold ${config.color} uppercase tracking-wider`}>
                      {config.label}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-silver/70 font-mono">
                    {activity.user_id}
                  </div>
                  {Object.keys(activity.details).length > 0 && (
                    <div className="mt-2 text-xs text-silver/60">
                      {Object.entries(activity.details).map(([key, value]) => (
                        <div key={key} className="truncate">
                          <span className="font-mono">{key}:</span> {String(value)}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-2 text-xs text-silver/50">
                    {new Date(activity.timestamp).toLocaleString()}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </motion.div>
  )
}
