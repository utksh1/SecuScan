import React from 'react'

type SkeletonProps = {
  lines?: number
  className?: string
  title?: string
}

export default function Skeleton({ lines = 3, className = '', title }: SkeletonProps) {
  return (
    <div role="status" aria-busy="true" className={`space-y-4 ${className}`}>
      {title ? (
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border border-accent-silver/20 rounded-full animate-spin" />
          <div className="text-sm font-mono uppercase tracking-wider text-silver/60">{title}</div>
        </div>
      ) : null}

      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className="h-4 bg-accent-silver/6 rounded-md animate-pulse" />
        ))}
      </div>

      <span className="sr-only">Loading...</span>
    </div>
  )
}
