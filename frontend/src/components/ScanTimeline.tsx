import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface ScanTimelineProps {
    status: string
    latestOutputLine?: string
}

type StageState = 'completed' | 'active' | 'pending' | 'failed'

const STAGES = [
    { key: 'queued', label: 'Target Queued' },
    { key: 'running', label: 'Scan Executing' },
    { key: 'finalizing', label: 'Report Generation' },
]

function getStageStates(status: string): StageState[] {
    const s = status.toLowerCase()
    if (s === 'pending' || s === 'queued') {
        return ['active', 'pending', 'pending']
    }
    if (s === 'running') {
        return ['completed', 'active', 'pending']
    }
    if (s === 'completed') {
        return ['completed', 'completed', 'completed']
    }
    if (s === 'failed') {
        return ['completed', 'failed', 'pending']
    }
    if (s === 'cancelled') {
        return ['completed', 'failed', 'pending']
    }
    return ['pending', 'pending', 'pending']
}

export default function ScanTimeline({ status, latestOutputLine }: ScanTimelineProps) {
    const states = getStageStates(status)
    const activeIndex = states.findIndex(s => s === 'active')

    return (
        <div className="border border-white/8 bg-charcoal p-6">
            <div className="flex items-center gap-4 mb-6">
                <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.36em] italic">Live Scan Timeline</h3>
                <div className="h-px flex-1 bg-white/8" />
            </div>

            <div className="flex flex-col md:flex-row md:items-start gap-6 md:gap-0">
                {STAGES.map((stage, idx) => {
                    const state = states[idx]
                    return (
                        <div key={stage.key} className="flex md:flex-1 items-start md:flex-col relative">
                            {idx < STAGES.length - 1 && (
                                <div className={`hidden md:block absolute top-4 left-1/2 w-full h-[2px] ${
                                    state === 'completed' ? 'bg-rag-green/60' : 'bg-white/10'
                                }`} style={{ zIndex: 0 }} />
                            )}

                            <div className="flex md:flex-col md:items-center gap-3 md:gap-2 relative z-10 md:w-full">
                                <div className={`w-8 h-8 shrink-0 flex items-center justify-center border-2 rounded-full ${
                                    state === 'completed'
                                        ? 'bg-rag-green/15 border-rag-green text-rag-green'
                                        : state === 'active'
                                            ? 'bg-rag-blue/15 border-rag-blue text-rag-blue'
                                            : state === 'failed'
                                                ? 'bg-rag-red/15 border-rag-red text-rag-red'
                                                : 'bg-white/[0.03] border-white/15 text-silver/30'
                                }`}>
                                    {state === 'completed' && <span className="text-xs font-black">✓</span>}
                                    {state === 'failed' && <span className="text-xs font-black">✕</span>}
                                    {state === 'active' && (
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                                            className="w-3 h-3 border-2 border-rag-blue border-t-transparent rounded-full"
                                        />
                                    )}
                                    {state === 'pending' && <span className="text-[10px] font-black">{idx + 1}</span>}
                                </div>

                                <div className="md:text-center">
                                    <p className={`text-[10px] font-black uppercase tracking-[0.2em] ${
                                        state === 'pending' ? 'text-silver/30' : 'text-silver-bright'
                                    }`}>
                                        {stage.label}
                                    </p>
                                    <AnimatePresence mode="wait">
                                        {state === 'active' && latestOutputLine && (
                                            <motion.p
                                                key={latestOutputLine}
                                                initial={{ opacity: 0, y: -4 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0 }}
                                                className="mt-1 text-[10px] font-mono text-rag-blue/80 truncate max-w-[220px] md:mx-auto"
                                            >
                                                {latestOutputLine}
                                            </motion.p>
                                        )}
                                    </AnimatePresence>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
