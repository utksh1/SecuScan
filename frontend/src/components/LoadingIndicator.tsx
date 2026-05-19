import React from 'react'
import { motion } from 'framer-motion'
import { HugeiconsIcon } from '@hugeicons/react'
import { Refresh01Icon, LoaderIcon } from '@hugeicons/core-free-icons'

interface LoadingIndicatorProps {
  message?: string
  size?: 'small' | 'medium' | 'large'
  variant?: 'spinner' | 'dots' | 'bars' | 'pulse'
  fullScreen?: boolean
  className?: string
}

function Icon({
  icon,
  size = 32,
  className = '',
}: {
  icon: any
  size?: number
  className?: string
}) {
  return <HugeiconsIcon icon={icon} size={size} strokeWidth={1.9} className={className} />
}

const sizeMap = {
  small: { icon: 24, container: 'py-8' },
  medium: { icon: 40, container: 'py-20' },
  large: { icon: 64, container: 'py-32' }
}

const spinnerVariants = {
  rotate: {
    rotate: 360,
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'linear'
    }
  }
}

const dotsVariants = {
  animate: {
    transition: {
      staggerChildren: 0.2
    }
  }
}

const dotVariants = {
  animate: {
    y: [-8, 0],
    opacity: [0.5, 1],
    transition: {
      duration: 0.8,
      repeat: Infinity,
      repeatType: 'reverse' as const
    }
  }
}

const barsVariants = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
}

const barVariants = {
  animate: {
    scaleY: [0.4, 1],
    opacity: [0.5, 1],
    transition: {
      duration: 0.6,
      repeat: Infinity,
      repeatType: 'reverse' as const
    }
  }
}

export function SpinnerIndicator({ size = 40 }: { size?: number }) {
  return (
    <motion.div variants={spinnerVariants} animate="rotate">
      <Icon icon={Refresh01Icon} size={size} className="text-silver/40" />
    </motion.div>
  )
}

export function DotsIndicator({ size = 12 }: { size?: number }) {
  return (
    <motion.div
      variants={dotsVariants}
      animate="animate"
      className="flex items-center gap-2"
    >
      {[...Array(3)].map((_, i) => (
        <motion.div
          key={i}
          variants={dotVariants}
          className={`w-${size} h-${size} rounded-full bg-silver/40`}
          style={{ width: size, height: size }}
        />
      ))}
    </motion.div>
  )
}

export function BarsIndicator({ size = 24 }: { size?: number }) {
  return (
    <motion.div
      variants={barsVariants}
      animate="animate"
      className="flex items-end gap-2 h-16"
    >
      {[...Array(4)].map((_, i) => (
        <motion.div
          key={i}
          variants={barVariants}
          className="w-1 bg-silver/40 rounded-full origin-bottom"
          style={{ height: (i + 1) * 16 }}
        />
      ))}
    </motion.div>
  )
}

export function PulseIndicator() {
  return (
    <motion.div
      animate={{
        scale: [0.8, 1, 0.8],
        opacity: [0.5, 1, 0.5]
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: 'easeInOut'
      }}
      className="w-12 h-12 rounded-full border-4 border-silver/40"
    />
  )
}

export default function LoadingIndicator({
  message = 'Loading...',
  size = 'medium',
  variant = 'spinner',
  fullScreen = false,
  className = ''
}: LoadingIndicatorProps) {
  const sizeConfig = sizeMap[size]

  const renderIndicator = () => {
    switch (variant) {
      case 'dots':
        return <DotsIndicator />
      case 'bars':
        return <BarsIndicator />
      case 'pulse':
        return <PulseIndicator />
      default:
        return <SpinnerIndicator size={sizeConfig.icon} />
    }
  }

  const containerClass = fullScreen
    ? 'fixed inset-0 flex items-center justify-center bg-charcoal-dark/80 backdrop-blur-sm z-50'
    : `flex flex-col items-center justify-center gap-6 ${sizeConfig.container} ${className}`

  return (
    <div className={containerClass}>
      <div className="flex flex-col items-center gap-6">
        {renderIndicator()}
        {message && (
          <motion.p
            animate={{ opacity: [0.6, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="text-xs md:text-sm font-black uppercase tracking-[0.3em] text-silver/50 italic text-center"
          >
            {message}
          </motion.p>
        )}
      </div>
    </div>
  )
}

// Progress indicator for multi-step operations
export function ProgressIndicator({
  current = 0,
  total = 10,
  message = 'Processing...'
}: {
  current?: number
  total?: number
  message?: string
}) {
  const percentage = (current / total) * 100

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <p className="text-xs font-black text-silver/50 uppercase tracking-widest italic">
            {message}
          </p>
          <span className="text-[10px] font-mono text-silver/40 uppercase font-black">
            {current} / {total}
          </span>
        </div>
        <div className="w-full h-2 bg-charcoal-dark border-2 border-black overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.5 }}
            className="h-full bg-rag-green"
          />
        </div>
      </div>
    </div>
  )
}

// Skeleton with loading indicator overlay
export function LoadingOverlay({ message = 'Loading...' }: { message?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 bg-charcoal-dark/60 backdrop-blur-sm flex items-center justify-center rounded-lg"
    >
      <div className="flex flex-col items-center gap-4">
        <SpinnerIndicator size={48} />
        <p className="text-xs font-black text-silver-bright uppercase tracking-widest">{message}</p>
      </div>
    </motion.div>
  )
}
