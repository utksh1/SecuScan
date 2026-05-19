import React from 'react'
import { motion } from 'framer-motion'

interface LoadingSkeletonProps {
  count?: number
  type?: 'card' | 'list-item' | 'table-row' | 'metric' | 'chart'
  className?: string
}

const skeletonVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
}

const shimmer = {
  animate: {
    backgroundPosition: ['0% 0%', '100% 0%']
  }
}

export function CardSkeleton() {
  return (
    <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="flex justify-between items-start gap-4">
          <div className="flex-1 space-y-3">
            <div className="h-8 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner w-3/4 rounded-sm animate-pulse"></div>
            <div className="h-4 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner w-1/2 rounded-sm animate-pulse"></div>
          </div>
          <div className="w-6 h-6 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner rounded-sm animate-pulse"></div>
        </div>

        {/* Content skeleton */}
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-3 bg-gradient-to-r from-silver/5 to-silver/10 border border-black/10 shadow-inner rounded-sm animate-pulse" style={{ width: `${100 - i * 15}%` }}></div>
          ))}
        </div>

        {/* Footer skeleton */}
        <div className="flex gap-3 pt-4">
          <div className="h-10 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner flex-1 rounded-sm animate-pulse"></div>
          <div className="h-10 w-20 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner rounded-sm animate-pulse"></div>
        </div>
      </div>
    </div>
  )
}

export function ListItemSkeleton() {
  return (
    <div className="relative md:pl-20 mb-8">
      {/* Timeline node skeleton */}
      <div className="absolute left-[31px] top-12 w-5 h-5 border-4 border-black/20 hidden md:block bg-silver/5 animate-pulse"></div>

      <div className="bg-charcoal border-4 border-black/20 p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
        <div className="space-y-6">
          {/* Top row skeleton */}
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 border-4 border-black/20 bg-silver/5 rounded-sm animate-pulse"></div>
            <div className="flex gap-4 flex-1">
              <div className="h-4 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner w-24 rounded-sm animate-pulse"></div>
              <div className="h-4 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 shadow-inner flex-1 rounded-sm animate-pulse"></div>
            </div>
          </div>

          {/* Content skeleton */}
          <div className="space-y-3 ml-14">
            {[1, 2].map((i) => (
              <div key={i} className="h-3 bg-gradient-to-r from-silver/5 to-silver/10 border border-black/10 shadow-inner rounded-sm animate-pulse" style={{ width: `${100 - i * 20}%` }}></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export function MetricSkeleton() {
  return (
    <div className="bg-gradient-to-br from-silver/5 to-silver/10 border-4 border-black/20 p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col justify-between h-40">
      <div className="flex justify-between items-start">
        <div className="h-4 bg-gradient-to-r from-silver/20 to-silver/30 border border-black/10 w-24 rounded-sm animate-pulse"></div>
        <div className="w-6 h-6 bg-gradient-to-r from-silver/20 to-silver/30 border border-black/10 rounded-sm animate-pulse"></div>
      </div>
      <div className="flex items-baseline gap-2">
        <div className="h-12 bg-gradient-to-r from-silver/20 to-silver/30 border border-black/10 w-32 rounded-sm animate-pulse"></div>
        <div className="h-3 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 w-16 rounded-sm animate-pulse"></div>
      </div>
    </div>
  )
}

export function TableRowSkeleton() {
  return (
    <div className="bg-charcoal border-b-2 border-black/10 p-4 flex items-center gap-4">
      <div className="w-8 h-8 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 rounded-sm animate-pulse"></div>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex-1 h-4 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 rounded-sm animate-pulse"></div>
      ))}
      <div className="w-20 h-8 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 rounded-sm animate-pulse"></div>
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="bg-charcoal border-4 border-black p-8 space-y-6">
      <div className="h-6 bg-gradient-to-r from-silver/10 to-silver/20 border border-black/10 w-1/3 rounded-sm animate-pulse"></div>
      <div className="flex items-end justify-between gap-2 h-48">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="flex-1 bg-gradient-to-t from-silver/20 to-silver/10 border-2 border-black/10 rounded-t-sm animate-pulse" style={{ height: `${Math.random() * 80 + 20}%` }}></div>
        ))}
      </div>
    </div>
  )
}

export default function LoadingSkeleton({ count = 3, type = 'card', className = '' }: LoadingSkeletonProps) {
  const renderSkeleton = () => {
    switch (type) {
      case 'list-item':
        return <ListItemSkeleton />
      case 'table-row':
        return <TableRowSkeleton />
      case 'metric':
        return <MetricSkeleton />
      case 'chart':
        return <ChartSkeleton />
      default:
        return <CardSkeleton />
    }
  }

  return (
    <motion.div
      variants={skeletonVariants}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {Array.from({ length: count }).map((_, i) => (
        <motion.div key={i} variants={itemVariants}>
          {renderSkeleton()}
        </motion.div>
      ))}
    </motion.div>
  )
}
