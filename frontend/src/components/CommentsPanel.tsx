import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { getComments, postComment, CommentRecord } from '../api'
import { useToast } from './ToastContext'

interface CommentsPanelProps {
  findingId: string
  isOpen: boolean
  onToggle: () => void
}

export default function CommentsPanel({ findingId, isOpen, onToggle }: CommentsPanelProps) {
  const [comments, setComments] = useState<CommentRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [composing, setComposing] = useState(false)
  const [content, setContent] = useState('')
  const { showToast } = useToast()

  useEffect(() => {
    if (isOpen) {
      loadComments()
    }
  }, [isOpen, findingId])

  const loadComments = async () => {
    setLoading(true)
    try {
      const data = await getComments(findingId)
      setComments(data.comments || [])
    } catch (error) {
      showToast('Failed to load comments', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleAddComment = async () => {
    if (!content.trim()) return

    setComposing(true)
    try {
      const newComment = await postComment(findingId, content)
      setComments([...comments, newComment])
      setContent('')
      showToast('Comment added successfully', 'success')
    } catch (error) {
      showToast('Failed to add comment', 'error')
    } finally {
      setComposing(false)
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="mb-6 rounded border border-silver-bright/20 bg-charcoal-dark px-4 py-2 text-xs font-bold uppercase tracking-widest text-silver-bright hover:border-silver-bright/50 hover:bg-charcoal/80 transition-all"
      >
        Comments ({comments.length})
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
        <h3 className="text-sm font-bold uppercase tracking-widest text-silver-bright">Comments</h3>
        <button
          onClick={onToggle}
          className="text-xs text-silver-bright/60 hover:text-silver-bright transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Comments List */}
      <div className="mb-4 max-h-64 space-y-3 overflow-y-auto">
        {loading ? (
          <div className="text-center text-xs text-silver/60">Loading comments...</div>
        ) : comments.length === 0 ? (
          <div className="text-center text-xs text-silver/60">No comments yet. Be the first to share insights!</div>
        ) : (
          comments.map((comment) => (
            <div key={comment.id} className="rounded bg-charcoal/40 border-l-2 border-rag-blue px-3 py-2">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-xs font-mono text-silver/70">{comment.user_id}</div>
                  <p className="mt-1 text-sm text-silver-bright leading-relaxed">{comment.content}</p>
                </div>
              </div>
              <div className="mt-2 text-xs text-silver/50">
                {new Date(comment.created_at).toLocaleString()}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Comment Composer */}
      <div className="border-t border-silver-bright/10 pt-4">
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Add a comment..."
          className="mb-2 w-full resize-none rounded border border-silver-bright/20 bg-charcoal px-3 py-2 text-xs text-silver-bright placeholder-silver/40 focus:border-rag-blue focus:outline-none"
          rows={3}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={() => setContent('')}
            className="rounded border border-silver-bright/20 bg-charcoal px-3 py-1 text-xs font-bold text-silver-bright hover:border-silver-bright/50 transition-all"
          >
            Clear
          </button>
          <button
            onClick={handleAddComment}
            disabled={composing || !content.trim()}
            className="rounded bg-rag-blue px-3 py-1 text-xs font-bold text-black hover:bg-rag-blue/90 disabled:opacity-50 transition-all"
          >
            {composing ? 'Adding...' : 'Add Comment'}
          </button>
        </div>
      </div>
    </motion.div>
  )
}
