import React, { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

type Node = {
  id: string
  label: string
  type: 'asset' | 'entry' | 'center'
  risk?: string
  category?: string
  x: number
  y: number
  connections: string[]
  data?: any
}

type NetworkMapProps = {
  assets: any[]
  entries: any[]
}

export default function NetworkMap({ assets, entries }: NetworkMapProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  
  // Calculate layout
  const nodes = useMemo(() => {
    const centerNode: Node = { id: 'center', label: 'SECUSCAN_CORE', type: 'center', x: 0, y: 0, connections: [] }
    const result: Node[] = [centerNode]
    
    // Assets in inner orbit
    const assetRadius = 180
    assets.forEach((asset, i) => {
      const angle = (i / assets.length) * Math.PI * 2
      const x = Math.cos(angle) * assetRadius
      const y = Math.sin(angle) * assetRadius
      
      result.push({
        id: asset.id,
        label: asset.target,
        type: 'asset',
        risk: asset.risk_level,
        x,
        y,
        connections: ['center'],
        data: asset
      })
      
      // Entries for this asset in outer orbit
      const assetEntries = entries.filter(e => e.asset_id === asset.id)
      const entryRadius = 320
      assetEntries.forEach((entry, j) => {
        const spread = Math.PI / 3 // 60 degree spread
        const offset = (j - (assetEntries.length - 1) / 2) * (spread / Math.max(assetEntries.length, 1))
        const entryAngle = angle + offset
        const ex = Math.cos(entryAngle) * entryRadius
        const ey = Math.sin(entryAngle) * entryRadius
        
        result.push({
          id: entry.id,
          label: entry.item,
          type: 'entry',
          risk: entry.risk,
          category: entry.category,
          x: ex,
          y: ey,
          connections: [asset.id],
          data: entry
        })
      })
    })
    
    return result
  }, [assets, entries])

  const selectedNode = useMemo(() => nodes.find(n => n.id === selectedNodeId), [nodes, selectedNodeId])

  const getColor = (risk?: string) => {
    switch (risk) {
      case 'critical': return 'var(--color-rag-red)'
      case 'high': return 'var(--color-rag-amber)'
      case 'medium': return 'var(--color-rag-blue)'
      case 'low': return 'var(--color-rag-green)'
      default: return 'var(--color-silver-muted)'
    }
  }

  const getBorderColor = (risk?: string) => {
    switch (risk) {
        case 'critical': return 'border-rag-red'
        case 'high': return 'border-rag-amber'
        case 'medium': return 'border-rag-blue'
        case 'low': return 'border-rag-green'
        default: return 'border-accent-silver/20'
    }
  }

  return (
    <div className="w-full h-[700px] bg-charcoal-dark border border-accent-silver/10 rounded-sm relative overflow-hidden group shadow-2xl executive-border">
      {/* Background Grid & Texture */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#3f3f46_1px,transparent_1px)] [background-size:24px_24px] group-hover:scale-110 transition-transform duration-[10s]"></div>
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[linear-gradient(to_right,#3f3f46_1px,transparent_1px),linear-gradient(to_bottom,#3f3f46_1px,transparent_1px)] [background-size:120px_120px]"></div>
      
      {/* Tactical Overlays */}
      <div className="absolute top-10 left-10 space-y-4 pointer-events-none z-10">
        <div>
            <h4 className="text-[11px] font-bold text-silver-bright uppercase tracking-[0.5em] italic leading-none mb-4">Tactical Topology Scan</h4>
            <div className="flex gap-6 items-center flex-wrap">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-silver-bright rotate-45 border border-white/20"></div>
                    <span className="text-[9px] text-silver/40 uppercase tracking-widest font-mono">Enclave Core</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 border-2 border-silver/20 bg-charcoal rounded-full"></div>
                    <span className="text-[9px] text-silver/40 uppercase tracking-widest font-mono">Infrastructure Node</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-accent-silver/40 rotate-45"></div>
                    <span className="text-[9px] text-silver/40 uppercase tracking-widest font-mono">Surface Vector</span>
                </div>
            </div>
        </div>
        <div className="h-px w-64 bg-accent-silver/5"></div>
        <div className="flex flex-col gap-2">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(risk => (
                <div key={risk} className="flex items-center gap-3">
                    <div className={`w-3 h-0.5 ${risk === 'CRITICAL' ? 'bg-rag-red' : risk === 'HIGH' ? 'bg-rag-amber' : risk === 'MEDIUM' ? 'bg-rag-blue' : 'bg-rag-green'}`}></div>
                    <span className="text-[8px] text-silver/20 uppercase tracking-[0.3em] font-mono">{risk}_SIGNAL_DELIMITER</span>
                </div>
            ))}
        </div>
      </div>

      <div className="absolute bottom-10 right-10 text-right pointer-events-none z-10">
        <span className="text-[10px] font-mono text-silver-bright/60 uppercase italic block mb-1">INTERCEPTION_MODE: CONTINUOUS</span>
        <span className="text-[8px] font-mono text-silver/20 uppercase tracking-[0.4em]">Node Distribution Index: {nodes.length} Targets</span>
      </div>

      {/* Main Graph Area */}
      <svg 
        viewBox="-450 -450 900 900" 
        className="w-full h-full cursor-crosshair select-none"
      >
        {/* Connection Rails */}
        <g opacity="0.1">
          {nodes.map(node => node.connections.map(connId => {
            const target = nodes.find(n => n.id === connId)
            if (!target) return null
            const isRelated = hoveredNode === node.id || hoveredNode === target.id || selectedNodeId === node.id || selectedNodeId === target.id
            return (
              <motion.line
                key={`${node.id}-${connId}`}
                x1={node.x} y1={node.y}
                x2={target.x} y2={target.y}
                stroke="currentColor"
                strokeWidth={isRelated ? 1.5 : 0.5}
                strokeDasharray={node.type === 'entry' ? "4 4" : "none"}
                className={isRelated ? 'text-silver-bright opacity-100' : 'text-silver opacity-20'}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.5, ease: "easeOut" }}
              />
            )
          }))}
        </g>

        {/* Nodes */}
        <AnimatePresence mode="popLayout">
          {nodes.map(node => (
            <g 
                key={node.id} 
                className="cursor-pointer"
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => setSelectedNodeId(node.id === selectedNodeId ? null : node.id)}
            >
              {/* Interaction Ring */}
              {(hoveredNode === node.id || selectedNodeId === node.id) && (
                <motion.circle 
                  cx={node.x} cy={node.y} r={node.type === 'entry' ? 12 : 18} 
                  fill="none"
                  stroke={getColor(node.risk)} 
                  strokeWidth="0.5"
                  strokeDasharray="4 4"
                  initial={{ rotate: 0, opacity: 0 }}
                  animate={{ rotate: 360, opacity: 0.4 }}
                  transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                />
              )}

              {/* Node Icon */}
              {node.type === 'center' ? (
                <motion.path
                  d="M-8,0 L0,-8 L8,0 L0,8 Z"
                  transform={`translate(${node.x},${node.y})`}
                  fill="#f4f4f5"
                  stroke="#3f3f46"
                  strokeWidth="2"
                  animate={{ scale: [1, 1.2, 1], rotate: [45, 135, 225, 315, 405] }}
                  transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
                />
              ) : node.type === 'asset' ? (
                 <motion.g transform={`translate(${node.x},${node.y})`}>
                    <circle 
                      r={5} 
                      fill={selectedNodeId === node.id ? '#f4f4f5' : '#121214'}
                      stroke={getColor(node.risk)}
                      strokeWidth={2}
                    />
                    <circle r={10} fill="none" stroke={getColor(node.risk)} strokeWidth="0.5" opacity="0.3" />
                 </motion.g>
              ) : (
                <motion.rect
                  x={node.x - 3} y={node.y - 3} width={6} height={6}
                  fill={selectedNodeId === node.id ? '#f4f4f5' : getColor(node.risk)}
                  className="rotate-45"
                  initial={{ opacity: 0.4 }}
                  animate={{ opacity: hoveredNode === node.id ? 1 : 0.6 }}
                />
              )}

              {/* Dynamic Labels */}
              <AnimatePresence>
                {(hoveredNode === node.id || selectedNodeId === node.id || node.type === 'asset' || node.type === 'center') && (
                    <motion.g
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    >
                    <text
                        x={node.x} y={node.y + (node.type === 'entry' ? -18 : 24)}
                        textAnchor="middle"
                        className={`text-[9px] font-mono font-bold uppercase tracking-[0.2em] pointer-events-none ${
                        selectedNodeId === node.id ? 'fill-silver-bright' : 'fill-silver/60'
                        }`}
                        style={{ textShadow: '0px 0px 8px rgba(0,0,0,0.9)' }}
                    >
                        {node.label}
                    </text>
                    {(hoveredNode === node.id || selectedNodeId === node.id) && node.category && (
                        <text
                            x={node.x} y={node.y + (node.type === 'entry' ? -30 : 36)}
                            textAnchor="middle"
                            className="text-[7px] font-mono font-light uppercase tracking-[0.3em] fill-silver/30 pointer-events-none italic"
                        >
                            {node.category}
                        </text>
                    )}
                    </motion.g>
                )}
              </AnimatePresence>
            </g>
          ))}
        </AnimatePresence>

        {/* Decorative Scanners Rails */}
        <circle cx="0" cy="0" r="180" fill="none" stroke="#3f3f46" strokeWidth="0.5" strokeDasharray="4 4" opacity="0.1" />
        <circle cx="0" cy="0" r="320" fill="none" stroke="#3f3f46" strokeWidth="0.5" strokeDasharray="12 12" opacity="0.05" />
        
        {/* Animated Radar Sweep */}
        <motion.circle
            cx="0" cy="0" r={450} fill="none" stroke="#f4f4f5" strokeWidth="1"
            initial={{ r: 0, opacity: 0 }}
            animate={{ r: 450, opacity: [0, 0.15, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
        />
      </svg>

      {/* Selected Node Details Side Panel (Executive Dossier) */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            className="absolute top-0 right-0 w-96 h-full bg-charcoal-dark border-l border-accent-silver/20 shadow-2xl z-20 overflow-y-auto"
          >
            <div className="p-10 space-y-10">
                <div className="flex justify-between items-start">
                    <div className="space-y-2">
                        <span className="text-[10px] text-silver/30 font-bold uppercase tracking-[0.5em] block">Object Telemetry</span>
                        <h3 className="text-xl font-serif font-light text-silver-bright italic uppercase tracking-tight">{selectedNode.label}</h3>
                    </div>
                    <button 
                        onClick={() => setSelectedNodeId(null)}
                        className="material-symbols-outlined text-silver/20 hover:text-white transition-colors"
                    >close</button>
                </div>

                <div className="h-px bg-accent-silver/10 w-full"></div>

                <div className="space-y-8">
                     <div className="grid grid-cols-2 gap-4">
                        <div className="p-6 bg-charcoal border border-accent-silver/10 space-y-2">
                            <span className="text-[8px] text-silver/20 uppercase font-bold tracking-widest block">Operational Risk</span>
                            <span className={`text-xs font-mono font-bold uppercase ${
                                selectedNode.risk === 'critical' ? 'text-rag-red' : 
                                selectedNode.risk === 'high' ? 'text-rag-amber' : 
                                'text-silver-bright'
                            }`}>{selectedNode.risk || 'SIGNAL_LOW'}</span>
                        </div>
                        <div className="p-6 bg-charcoal border border-accent-silver/10 space-y-2">
                            <span className="text-[8px] text-silver/20 uppercase font-bold tracking-widest block">Object Type</span>
                            <span className="text-xs font-mono text-silver-bright uppercase italic">{selectedNode.type}</span>
                        </div>
                     </div>

                     <div className="space-y-4">
                        <h4 className="text-[9px] font-bold text-silver/40 uppercase tracking-[0.3em] italic">Descriptive Metadata</h4>
                        <div className={`p-6 bg-charcoal-dark border-l-2 ${getBorderColor(selectedNode.risk)} space-y-4 shadow-inner`}>
                             {selectedNode.type === 'asset' ? (
                                <>
                                    <div className="space-y-1">
                                        <span className="text-[8px] text-silver/20 uppercase font-mono block">Associated Targets</span>
                                        <p className="text-[10px] text-silver-bright/80 font-mono italic">{selectedNode.data?.description || 'No direct descriptors found'}</p>
                                    </div>
                                    <div className="space-y-2 pt-2">
                                        <span className="text-[8px] text-silver/20 uppercase font-mono block">Status Verification</span>
                                        <div className="flex items-center gap-3">
                                            <div className={`w-1.5 h-1.5 rounded-full ${selectedNode.data?.status === 'active' ? 'bg-rag-green animate-pulse' : 'bg-silver/10'}`}></div>
                                            <span className="text-[9px] text-silver-bright font-mono uppercase tracking-widest">{selectedNode.data?.status || 'UNKNOWN_STATE'}</span>
                                        </div>
                                    </div>
                                </>
                             ) : (
                                <>
                                    <div className="space-y-1">
                                        <span className="text-[8px] text-silver/20 uppercase font-mono block">Intelligence Detail</span>
                                        <p className="text-[10px] text-silver-bright/80 font-mono italic">{selectedNode.data?.details || 'No detailed interception data'}</p>
                                    </div>
                                    <div className="space-y-1 pt-2">
                                        <span className="text-[8px] text-silver/20 uppercase font-mono block">Intelligence Source</span>
                                        <p className="text-[10px] text-silver-bright uppercase font-bold tracking-widest">{selectedNode.data?.source || 'ANONYMOUS_PROBE'}</p>
                                    </div>
                                </>
                             )}
                        </div>
                     </div>
                </div>

                <div className="pt-10 space-y-4">
                    <button className="w-full py-5 bg-silver-bright text-charcoal-dark font-black text-[10px] uppercase tracking-[0.4em] hover:bg-white transition-all italic flex items-center justify-center gap-3 group">
                        Enter Deep Dive Matrix
                        <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
                    </button>
                    <p className="text-[8px] text-silver/20 uppercase text-center tracking-[0.2em] font-mono">End of Briefing Ledger</p>
                </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

