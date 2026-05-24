import React, { useEffect, useState, useMemo, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getAssets, getAssetsGraph, getAssetDetails, getFindingDetails } from '../api'
import { routePath, routes } from '../routes'
import { formatLocaleDate } from '../utils/date'

interface Asset {
  id: string
  type: 'host' | 'service'
  name: string
  host_id: string | null
  host_name: string | null
  metadata: Record<string, any>
  created_at: string
  updated_at: string
  findings_count: number
  tasks_count: number
  reports_count: number
}

interface GraphNode {
  id: string
  label: string
  type: 'host' | 'service' | 'finding' | 'task' | 'report'
  x: number
  y: number
  vx: number
  vy: number
  details?: any
}

interface GraphLink {
  source: string
  target: string
  type: string
}

const severityConfig: Record<string, string> = {
  critical: 'bg-rag-red text-black border-rag-red/30',
  high: 'bg-rag-amber text-black border-rag-amber/30',
  medium: 'bg-rag-blue text-black border-rag-blue/30',
  low: 'bg-charcoal-dark text-silver-bright border border-silver-bright/15',
  info: 'bg-charcoal-dark text-silver border border-silver/15',
}

export default function Assets() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'list' | 'graph'>('list')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'host' | 'service'>('all')
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null)
  const [selectedAssetDetails, setSelectedAssetDetails] = useState<any>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const navigate = useNavigate()

  // Graph state
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const panStart = useRef({ x: 0, y: 0 })
  const dragNodeId = useRef<string | null>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const animationFrameId = useRef<number | null>(null)

  // Highlight state
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)

  // Fetch standard asset list
  const loadAssetsData = () => {
    setLoading(true)
    getAssets()
      .then((data: any) => {
        setAssets(data.assets || [])
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }

  // Fetch graph details
  const loadGraphData = () => {
    getAssetsGraph()
      .then((data: any) => {
        // Initialize nodes with random positions near center
        const width = 800
        const height = 500
        const initializedNodes = (data.nodes || []).map((node: any) => ({
          ...node,
          x: width / 2 + (Math.random() - 0.5) * 200,
          y: height / 2 + (Math.random() - 0.5) * 200,
          vx: 0,
          vy: 0,
        }))
        setGraphData({
          nodes: initializedNodes,
          links: data.links || [],
        })
      })
      .catch((err) => console.error(err))
  }

  useEffect(() => {
    loadAssetsData()
    loadGraphData()

    const params = new URLSearchParams(window.location.search)
    const selected = params.get('selected')
    if (selected) {
      setSelectedAssetId(selected)
      setActiveTab('list')
    }
  }, [])

  useEffect(() => {
    const handleLocationChange = () => {
      const params = new URLSearchParams(window.location.search)
      const selected = params.get('selected')
      if (selected) {
        setSelectedAssetId(selected)
        setActiveTab('list')
      }
    }
    window.addEventListener('popstate', handleLocationChange)
    const interval = setInterval(handleLocationChange, 500)
    return () => {
      window.removeEventListener('popstate', handleLocationChange)
      clearInterval(interval)
    }
  }, [])

  // Poll for updates in graph or lists
  useEffect(() => {
    const interval = setInterval(() => {
      getAssets().then((data: any) => setAssets(data.assets || []))
      // Only poll graph if active to reduce computations
      if (activeTab === 'graph') {
        getAssetsGraph().then((data: any) => {
          setGraphData((prev) => {
            const nextNodes = (data.nodes || []).map((n: any) => {
              const existing = prev.nodes.find((en) => en.id === n.id)
              return existing ? { ...n, x: existing.x, y: existing.y, vx: existing.vx, vy: existing.vy } : { ...n, x: 400 + (Math.random() - 0.5) * 100, y: 250 + (Math.random() - 0.5) * 100, vx: 0, vy: 0 }
            })
            return { nodes: nextNodes, links: data.links || [] }
          })
        })
      }
    }, 15000)
    return () => clearInterval(interval)
  }, [activeTab])

  // Fetch single asset details when selected
  useEffect(() => {
    if (!selectedAssetId) {
      setSelectedAssetDetails(null)
      return
    }
    let active = true
    setDetailsLoading(true)
    // Extract real ID if it's prefix (finding details handle separately)
    const isAsset = selectedAssetId.startsWith('asset:')
    if (isAsset) {
      getAssetDetails(selectedAssetId)
        .then((data: any) => {
          if (active) {
            setSelectedAssetDetails({ ...data, isDirectAsset: true })
          }
        })
        .catch((err) => {
          if (active) {
            console.error(err)
          }
        })
        .finally(() => {
          if (active) {
            setDetailsLoading(false)
          }
        })
    } else {
      // It is a finding, task, or report node clicked in the graph
      // Let's resolve its details accordingly
      const parts = selectedAssetId.split(':')
      const type = parts[0]
      if (type === 'finding') {
        getFindingDetails(selectedAssetId)
          .then((data: any) => {
            if (active) {
              setSelectedAssetDetails({ ...data, type: 'finding', label: data.title })
            }
          })
          .catch((err) => {
            if (active) {
              console.error(err)
            }
          })
          .finally(() => {
            if (active) {
              setDetailsLoading(false)
            }
          })
      } else if (type === 'report') {
        if (active) {
          setSelectedAssetDetails({ id: selectedAssetId, type: 'report', label: 'PDF/HTML Security Report' })
          setDetailsLoading(false)
        }
      } else {
        // Task
        if (active) {
          setSelectedAssetDetails({ id: selectedAssetId, type: 'task', label: 'Scan Task Record' })
          setDetailsLoading(false)
        }
      }
    }
    return () => {
      active = false
    }
  }, [selectedAssetId])

  // Force-directed simulation loop
  useEffect(() => {
    if (activeTab !== 'graph' || graphData.nodes.length === 0) return

    const width = 800
    const height = 500
    const centerX = width / 2
    const centerY = height / 2

    // Physics constants
    const kRepulsion = 1200
    const kAttraction = 0.04
    const restLength = 80
    const kGravity = 0.015
    const friction = 0.85

    const step = () => {
      setGraphData((prev) => {
        const nodes = prev.nodes.map((n) => ({ ...n }))
        const links = prev.links

        // 1. Repulsion between all nodes
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const n1 = nodes[i]
            const n2 = nodes[j]
            const dx = n2.x - n1.x
            const dy = n2.y - n1.y
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            if (dist < 300) {
              const force = kRepulsion / (dist * dist)
              const fx = (dx / dist) * force
              const fy = (dy / dist) * force

              if (n1.id !== dragNodeId.current) {
                n1.vx -= fx
                n1.vy -= fy
              }
              if (n2.id !== dragNodeId.current) {
                n2.vx += fx
                n2.vy += fy
              }
            }
          }
        }

        // 2. Attraction along links
        links.forEach((link) => {
          const sourceNode = nodes.find((n) => n.id === link.source)
          const targetNode = nodes.find((n) => n.id === link.target)
          if (!sourceNode || !targetNode) return

          const dx = targetNode.x - sourceNode.x
          const dy = targetNode.y - sourceNode.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = kAttraction * (dist - restLength)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force

          if (sourceNode.id !== dragNodeId.current) {
            sourceNode.vx += fx
            sourceNode.vy += fy
          }
          if (targetNode.id !== dragNodeId.current) {
            targetNode.vx -= fx
            targetNode.vy -= fy
          }
        })

        // 3. Gravity & Update Positions
        nodes.forEach((n) => {
          if (n.id === dragNodeId.current) return

          const dx = centerX - n.x
          const dy = centerY - n.y
          n.vx += dx * kGravity
          n.vy += dy * kGravity

          // Apply velocity and friction
          n.x += n.vx
          n.y += n.vy
          n.vx *= friction
          n.vy *= friction

          // Bound within viewport
          n.x = Math.max(40, Math.min(width - 40, n.x))
          n.y = Math.max(40, Math.min(height - 40, n.y))
        })

        return { nodes, links }
      })

      animationFrameId.current = requestAnimationFrame(step)
    }

    animationFrameId.current = requestAnimationFrame(step)
    return () => {
      if (animationFrameId.current) cancelAnimationFrame(animationFrameId.current)
    }
  }, [activeTab, graphData.nodes.length])

  // Filter list
  const filteredAssets = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return assets.filter((asset) => {
      const matchesType = filterType === 'all' || asset.type === filterType
      const matchesSearch =
        asset.name.toLowerCase().includes(query) ||
        (asset.host_name && asset.host_name.toLowerCase().includes(query)) ||
        (asset.type && asset.type.toLowerCase().includes(query))
      return matchesType && matchesSearch
    })
  }, [assets, searchQuery, filterType])

  // Node colors & icons based on Type
  const getNodeStyles = (type: string, severity?: string) => {
    switch (type) {
      case 'host':
        return { color: '#3b82f6', icon: 'dns', border: 'border-blue-500', glow: 'shadow-[0_0_12px_rgba(59,130,246,0.5)]' }
      case 'service':
        return { color: '#a855f7', icon: 'lan', border: 'border-purple-500', glow: 'shadow-[0_0_12px_rgba(168,85,247,0.5)]' }
      case 'finding':
        const sev = (severity || 'low').toLowerCase()
        const col = sev === 'critical' || sev === 'high' ? '#ef4444' : sev === 'medium' ? '#f59e0b' : '#3b82f6'
        return { color: col, icon: 'warning', border: 'border-red-500', glow: 'shadow-[0_0_12px_rgba(239,68,68,0.5)]' }
      case 'task':
        return { color: '#6b7280', icon: 'terminal', border: 'border-gray-500', glow: 'shadow-[0_0_12px_rgba(107,114,128,0.5)]' }
      case 'report':
        return { color: '#10b981', icon: 'summarize', border: 'border-emerald-500', glow: 'shadow-[0_0_12px_rgba(16,185,129,0.5)]' }
      default:
        return { color: '#9ca3af', icon: 'help', border: 'border-gray-400', glow: '' }
    }
  }

  // Pan / Zoom handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target instanceof SVGElement && e.target.tagName === 'svg') {
      setIsPanning(true)
      panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStart.current.x,
        y: e.clientY - panStart.current.y,
      })
    } else if (dragNodeId.current) {
      if (!svgRef.current) return
      const rect = svgRef.current.getBoundingClientRect()

      // Calculate coordinates relative to SVG local viewport
      const x = ((e.clientX - rect.left) / rect.width) * 800
      const y = ((e.clientY - rect.top) / rect.height) * 500

      setGraphData((prev) => {
        const nextNodes = prev.nodes.map((n) => {
          if (n.id === dragNodeId.current) {
            return { ...n, x, y, vx: 0, vy: 0 }
          }
          return n
        })
        return { ...prev, nodes: nextNodes }
      })
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
    dragNodeId.current = null
  }

  const handleNodeDragStart = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    dragNodeId.current = id
  }

  // Neighbor nodes highlight helper
  const adjacentNodeIds = useMemo(() => {
    if (!hoveredNodeId) return new Set<string>()
    const ids = new Set<string>([hoveredNodeId])
    graphData.links.forEach((link) => {
      if (link.source === hoveredNodeId) ids.add(link.target)
      if (link.target === hoveredNodeId) ids.add(link.source)
    })
    return ids
  }, [hoveredNodeId, graphData.links])

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver px-4 py-6 md:px-8 md:py-10">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8">

        {/* Header */}
        <header className="border-b-4 border-silver-bright/10 pb-8">
          <div className="mb-4 inline-block bg-rag-blue px-4 py-1 text-xs font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Network Topology v3.2
          </div>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="space-y-3">
              <h1 className="text-5xl font-black uppercase tracking-tighter text-silver-bright italic md:text-7xl">
                Assets <span className="text-transparent" style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}>Desk</span>
              </h1>
              <p className="text-xs font-mono uppercase tracking-[0.24em] text-silver/45">
                Active tracked surface // {assets.filter((a) => a.type === 'host').length} hosts // {assets.filter((a) => a.type === 'service').length} service endpoints
              </p>
            </div>

            {/* Toggle tabs */}
            <div className="flex bg-charcoal border-2 border-black p-1 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] w-fit">
              <button
                onClick={() => { setActiveTab('list'); setSelectedAssetId(null) }}
                className={`px-6 py-2.5 text-[10px] font-black uppercase tracking-[0.15em] transition-all ${
                  activeTab === 'list'
                    ? 'bg-silver-bright text-black shadow-[2px_2px_0px_rgba(0,0,0,1)]'
                    : 'text-silver/60 hover:text-silver-bright'
                }`}
              >
                Inventory List
              </button>
              <button
                onClick={() => { setActiveTab('graph'); setSelectedAssetId(null); loadGraphData() }}
                className={`px-6 py-2.5 text-[10px] font-black uppercase tracking-[0.15em] transition-all ${
                  activeTab === 'graph'
                    ? 'bg-silver-bright text-black shadow-[2px_2px_0px_rgba(0,0,0,1)]'
                    : 'text-silver/60 hover:text-silver-bright'
                }`}
              >
                Topology Graph
              </button>
            </div>
          </div>
        </header>

        {/* Content Panel split into main view and sidebar details */}
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.2fr)_420px]">

          {/* Main Workspace Area */}
          <main className="space-y-6">

            {activeTab === 'list' ? (
              /* --- INVENTORY LIST VIEW --- */
              <div className="space-y-6">

                {/* Search & Filters */}
                <div className="border-2 border-black bg-charcoal p-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search asset target, host name, or service port..."
                      className="h-11 w-full border-2 border-silver-bright/10 bg-charcoal-dark px-4 text-xs font-mono text-silver-bright placeholder:text-silver/20 focus:border-rag-blue focus:outline-none"
                    />
                    {searchQuery.trim() && (
                      <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-silver/50 hover:text-silver-bright">
                        ✕
                      </button>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => setFilterType('all')}
                      className={`h-11 border px-4 text-[10px] font-black uppercase tracking-[0.16em] transition-all ${
                        filterType === 'all'
                          ? 'border-black bg-silver-bright text-black shadow-[3px_3px_0px_rgba(0,0,0,1)]'
                          : 'border-silver-bright/10 bg-charcoal-dark text-silver/65 hover:border-silver-bright/30'
                      }`}
                    >
                      All Types
                    </button>
                    <button
                      onClick={() => setFilterType('host')}
                      className={`h-11 border px-4 text-[10px] font-black uppercase tracking-[0.16em] transition-all ${
                        filterType === 'host'
                          ? 'border-black bg-rag-blue text-black shadow-[3px_3px_0px_rgba(0,0,0,1)]'
                          : 'border-silver-bright/10 bg-charcoal-dark text-silver/65 hover:border-silver-bright/30'
                      }`}
                    >
                      Hosts
                    </button>
                    <button
                      onClick={() => setFilterType('service')}
                      className={`h-11 border px-4 text-[10px] font-black uppercase tracking-[0.16em] transition-all ${
                        filterType === 'service'
                          ? 'border-black bg-purple-500 text-black shadow-[3px_3px_0px_rgba(0,0,0,1)]'
                          : 'border-silver-bright/10 bg-charcoal-dark text-silver/65 hover:border-silver-bright/30'
                      }`}
                    >
                      Services
                    </button>
                  </div>
                </div>

                {/* Table Layout */}
                <div className="border-2 border-black bg-charcoal shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
                  {loading ? (
                    <div className="py-20 text-center uppercase tracking-widest text-silver/40 font-mono text-sm">
                      Retrieving tracked asset entities...
                    </div>
                  ) : filteredAssets.length === 0 ? (
                    <div className="py-20 text-center uppercase tracking-widest text-silver/30 font-mono text-sm italic">
                      No tracked asset models match filters.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse font-mono">
                        <thead>
                          <tr className="border-b border-silver-bright/10 text-xs font-black uppercase tracking-wider text-silver/45 bg-charcoal-dark/40">
                            <th className="px-6 py-4">Asset Target</th>
                            <th className="px-6 py-4">Type</th>
                            <th className="px-6 py-4">Parent Host</th>
                            <th className="px-6 py-4 text-center">Findings</th>
                            <th className="px-6 py-4 text-center">Tasks</th>
                            <th className="px-6 py-4 text-center">Reports</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-silver-bright/5 text-sm">
                          {filteredAssets.map((asset) => {
                            const isSelected = selectedAssetId === asset.id
                            const isHost = asset.type === 'host'
                            return (
                              <tr
                                key={asset.id}
                                onClick={() => setSelectedAssetId(asset.id)}
                                className={`cursor-pointer hover:bg-silver-bright/3 transition-colors ${
                                  isSelected ? 'bg-silver-bright/8 hover:bg-silver-bright/8' : ''
                                }`}
                              >
                                <td className="px-6 py-4 font-bold text-silver-bright uppercase">
                                  {asset.name}
                                </td>
                                <td className="px-6 py-4">
                                  <span className={`text-[9px] font-black px-2 py-0.5 border ${
                                    isHost
                                      ? 'text-rag-blue border-rag-blue/20 bg-rag-blue/5'
                                      : 'text-purple-400 border-purple-500/20 bg-purple-500/5'
                                  }`}>
                                    {asset.type.toUpperCase()}
                                  </span>
                                </td>
                                <td className="px-6 py-4 text-silver/50 uppercase">
                                  {asset.host_name || '—'}
                                </td>
                                <td className="px-6 py-4 text-center">
                                  <span className={`px-2 py-0.5 text-xs font-bold ${
                                    asset.findings_count > 0 ? 'text-rag-amber bg-rag-amber/10' : 'text-silver/30'
                                  }`}>
                                    {asset.findings_count.toString().padStart(2, '0')}
                                  </span>
                                </td>
                                <td className="px-6 py-4 text-center">
                                  <span className={`px-2 py-0.5 text-xs font-bold ${
                                    asset.tasks_count > 0 ? 'text-silver-bright bg-silver-bright/10' : 'text-silver/30'
                                  }`}>
                                    {asset.tasks_count.toString().padStart(2, '0')}
                                  </span>
                                </td>
                                <td className="px-6 py-4 text-center">
                                  <span className={`px-2 py-0.5 text-xs font-bold ${
                                    asset.reports_count > 0 ? 'text-rag-green bg-rag-green/10' : 'text-silver/30'
                                  }`}>
                                    {asset.reports_count.toString().padStart(2, '0')}
                                  </span>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* --- GRAPH TOPOLOGY VIEW --- */
              <div className="space-y-4">
                <div className="border-2 border-black bg-charcoal p-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] flex flex-wrap items-center justify-between gap-4">
                  <span className="text-xs font-mono text-silver/45 uppercase tracking-widest">
                    Interactive topology map // Drag nodes to position // Zoom: {Math.round(zoom * 100)}%
                  </span>

                  <div className="flex gap-2">
                    <button
                      onClick={() => setZoom((z) => Math.min(2.5, z + 0.1))}
                      className="w-10 h-10 border border-silver-bright/10 bg-charcoal-dark hover:border-silver-bright/35 flex items-center justify-center text-silver-bright"
                      title="Zoom In"
                    >
                      <span className="material-symbols-outlined text-[18px]">zoom_in</span>
                    </button>
                    <button
                      onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))}
                      className="w-10 h-10 border border-silver-bright/10 bg-charcoal-dark hover:border-silver-bright/35 flex items-center justify-center text-silver-bright"
                      title="Zoom Out"
                    >
                      <span className="material-symbols-outlined text-[18px]">zoom_out</span>
                    </button>
                    <button
                      onClick={() => { setZoom(1.0); setPan({ x: 0, y: 0 }) }}
                      className="h-10 px-3 border border-silver-bright/10 bg-charcoal-dark hover:border-silver-bright/35 flex items-center justify-center text-[10px] font-black uppercase tracking-wider text-silver-bright"
                      title="Reset Pan & Zoom"
                    >
                      RESET View
                    </button>
                  </div>
                </div>

                <div
                  className="border-2 border-black bg-charcoal-darker relative shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] overflow-hidden cursor-grab active:cursor-grabbing select-none"
                  style={{ height: '560px' }}
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                >
                  <svg
                    ref={svgRef}
                    className="w-full h-full"
                    viewBox="0 0 800 500"
                    preserveAspectRatio="xMidYMid meet"
                  >
                    {/* SVG Definitions for arrowheads, filters */}
                    <defs>
                      <marker
                        id="arrow"
                        viewBox="0 0 10 10"
                        refX="20"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#4b5563" opacity="0.5" />
                      </marker>
                    </defs>

                    {/* Scale and pan group */}
                    <g transform={`translate(${400 + pan.x}, ${250 + pan.y}) scale(${zoom}) translate(-400, -250)`}>

                      {/* Connection Lines (Links) */}
                      {graphData.links.map((link, idx) => {
                        const sourceNode = graphData.nodes.find((n) => n.id === link.source)
                        const targetNode = graphData.nodes.find((n) => n.id === link.target)
                        if (!sourceNode || !targetNode) return null

                        const isHighlighted = hoveredNodeId === null ||
                          (hoveredNodeId === link.source || hoveredNodeId === link.target)

                        return (
                          <line
                            key={`link-${idx}`}
                            x1={sourceNode.x}
                            y1={sourceNode.y}
                            x2={targetNode.x}
                            y2={targetNode.y}
                            stroke={isHighlighted ? '#4b5563' : '#1f2937'}
                            strokeWidth={isHighlighted ? 1.5 : 0.8}
                            strokeDasharray={link.type === 'has_service' ? 'none' : '4,4'}
                            opacity={isHighlighted ? 0.75 : 0.2}
                            markerEnd="url(#arrow)"
                            style={{ transition: 'stroke 0.2s, stroke-width 0.2s, opacity 0.2s' }}
                          />
                        )
                      })}

                      {/* Interactive Nodes */}
                      {graphData.nodes.map((node) => {
                        const styles = getNodeStyles(node.type, node.details?.severity)
                        const isHovered = hoveredNodeId === node.id
                        const isDimmed = hoveredNodeId !== null && !adjacentNodeIds.has(node.id)
                        const isSelected = selectedAssetId === node.id

                        return (
                          <g
                            key={node.id}
                            transform={`translate(${node.x}, ${node.y})`}
                            className="cursor-pointer"
                            onMouseDown={(e) => handleNodeDragStart(node.id, e)}
                            onClick={(e) => { e.stopPropagation(); setSelectedAssetId(node.id) }}
                            onMouseEnter={() => setHoveredNodeId(node.id)}
                            onMouseLeave={() => setHoveredNodeId(null)}
                            opacity={isDimmed ? 0.35 : 1.0}
                            style={{ transition: 'opacity 0.25s' }}
                          >
                            {/* Inner Circle Glow */}
                            {(isHovered || isSelected) && (
                              <circle
                                r="22"
                                fill="none"
                                stroke={styles.color}
                                strokeWidth="2"
                                opacity="0.3"
                                className="animate-pulse"
                              />
                            )}

                            {/* Node circle */}
                            <circle
                              r="16"
                              fill="#151719"
                              stroke={isSelected ? '#ffffff' : styles.color}
                              strokeWidth={isSelected ? 3.0 : 1.8}
                            />

                            {/* Node icon text */}
                            <text
                              className="material-symbols-outlined text-[16px] select-none font-bold"
                              textAnchor="middle"
                              dy="5"
                              fill={styles.color}
                              style={{ fontFamily: 'Material Symbols Outlined' }}
                            >
                              {styles.icon}
                            </text>

                            {/* Text labels */}
                            <text
                              y="28"
                              textAnchor="middle"
                              fill={isSelected ? '#ffffff' : '#9ca3af'}
                              className={`text-[8.5px] font-black font-mono uppercase tracking-wide select-none ${
                                isSelected ? 'bg-black px-1.5' : ''
                              }`}
                            >
                              {node.label.length > 20 ? `${node.label.slice(0, 18)}...` : node.label}
                            </text>
                          </g>
                        )
                      })}

                    </g>
                  </svg>
                </div>
              </div>
            )}
          </main>

          {/* Details Sidebar */}
          <aside className="xl:sticky xl:top-32 xl:self-start">
            <div className="border-4 border-black bg-charcoal shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] min-h-[480px]">

              <AnimatePresence mode="wait">
                {selectedAssetId ? (
                  detailsLoading ? (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="p-8 text-center uppercase tracking-widest text-xs font-mono text-silver/40 py-24"
                    >
                      Resolving node context...
                    </motion.div>
                  ) : selectedAssetDetails ? (
                    <motion.div
                      key="details"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="p-6 space-y-6"
                    >
                      {/* Sidebar Header */}
                      <div className="border-b border-silver-bright/8 pb-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className={`text-[9px] font-black px-2 py-0.5 uppercase tracking-widest border ${
                            selectedAssetDetails.type === 'host'
                              ? 'text-rag-blue border-rag-blue/20 bg-rag-blue/5'
                              : selectedAssetDetails.type === 'service'
                                ? 'text-purple-400 border-purple-500/20 bg-purple-500/5'
                                : 'text-silver-bright border-accent-silver/20'
                          }`}>
                            {selectedAssetDetails.type?.toUpperCase()}
                          </span>

                          <button
                            onClick={() => setSelectedAssetId(null)}
                            className="text-silver/40 hover:text-white text-xs uppercase tracking-widest font-mono"
                          >
                            Close ✕
                          </button>
                        </div>

                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-silver/35">Selected Model</p>
                        <h2 className="text-2xl font-black uppercase italic tracking-tight text-silver-bright break-all">
                          {selectedAssetDetails.name || selectedAssetDetails.label}
                        </h2>
                      </div>

                      {/* Model Properties Grid */}
                      {selectedAssetDetails.isDirectAsset ? (
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                            <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Target Name</p>
                            <p className="mt-2 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright break-all">
                              {selectedAssetDetails.name}
                            </p>
                          </div>

                          <div className="border border-silver-bright/8 bg-charcoal-dark p-3">
                            <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Host Reference</p>
                            <p className="mt-2 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">
                              {selectedAssetDetails.host_name || 'Self/Parent'}
                            </p>
                          </div>

                          <div className="border border-silver-bright/8 bg-charcoal-dark p-3 col-span-2">
                            <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35">Discovered On</p>
                            <p className="mt-2 text-xs font-mono uppercase tracking-[0.14em] text-silver-bright">
                              {formatLocaleDate(selectedAssetDetails.created_at)}
                            </p>
                          </div>

                          {/* Render meta fields if present */}
                          {selectedAssetDetails.metadata && Object.keys(selectedAssetDetails.metadata).length > 0 && (
                            <div className="border border-silver-bright/8 bg-charcoal-dark p-3 col-span-2 space-y-1">
                              <p className="text-[9px] font-black uppercase tracking-[0.2em] text-silver/35 mb-2">Technical Metadata</p>
                              {Object.entries(selectedAssetDetails.metadata).map(([key, val]) => (
                                <div key={key} className="flex justify-between text-[11px] font-mono">
                                  <span className="text-silver/40 uppercase">{key}:</span>
                                  <span className="text-silver-bright font-semibold">{String(val)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        /* Finding, Task, or Report properties */
                        <div className="space-y-4">
                          {selectedAssetDetails.type === 'finding' && (
                            <div className="space-y-4">
                              <div className="border-l-4 border-rag-red bg-charcoal-dark p-4">
                                <p className="text-xs font-black uppercase tracking-widest text-rag-red mb-1">Severity: {selectedAssetDetails.severity?.toUpperCase()}</p>
                                <p className="text-xs font-mono uppercase tracking-wide text-silver/50 mb-2">Category: {selectedAssetDetails.category}</p>
                                <p className="text-xs leading-relaxed text-silver/80">{selectedAssetDetails.description}</p>
                              </div>

                              <Link
                                to={routes.findings}
                                className="block w-full py-2.5 bg-silver-bright text-black font-black uppercase text-[10px] tracking-widest text-center shadow-[4px_4px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all"
                              >
                                View in Findings Desk
                              </Link>
                            </div>
                          )}

                          {selectedAssetDetails.type === 'task' && (
                            <div className="space-y-4">
                              <div className="border-l-4 border-gray-500 bg-charcoal-dark p-4">
                                <p className="text-xs font-black uppercase tracking-widest text-silver-bright mb-1">Scanner Task</p>
                                <p className="text-xs font-mono uppercase tracking-wide text-silver/50">ID: {selectedAssetDetails.id?.slice(0, 16)}</p>
                              </div>

                              <Link
                                to={routePath.task(selectedAssetDetails.id)}
                                className="block w-full py-2.5 bg-silver-bright text-black font-black uppercase text-[10px] tracking-widest text-center shadow-[4px_4px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all"
                              >
                                View Task Execution Log
                              </Link>
                            </div>
                          )}

                          {selectedAssetDetails.type === 'report' && (
                            <div className="space-y-4">
                              <div className="border-l-4 border-rag-green bg-charcoal-dark p-4">
                                <p className="text-xs font-black uppercase tracking-widest text-rag-green mb-1">Vulnerability Report</p>
                                <p className="text-xs font-mono uppercase tracking-wide text-silver/50">Generated for associated tasks.</p>
                              </div>

                              <Link
                                to={routes.reports}
                                className="block w-full py-2.5 bg-silver-bright text-black font-black uppercase text-[10px] tracking-widest text-center shadow-[4px_4px_0px_rgba(0,0,0,1)] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none transition-all"
                              >
                                Open Reports Ledger
                              </Link>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Connected lists for assets */}
                      {selectedAssetDetails.isDirectAsset && (
                        <div className="space-y-5 border-t border-silver-bright/8 pt-5 font-mono">
                          {/* Linked Findings */}
                          <div>
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-silver/45 mb-2 flex justify-between">
                              <span>Linked Findings</span>
                              <span>({selectedAssetDetails.findings?.length || 0})</span>
                            </h3>
                            {(!selectedAssetDetails.findings || selectedAssetDetails.findings.length === 0) ? (
                              <p className="text-[10px] uppercase text-silver/30 italic">No vulnerability findings.</p>
                            ) : (
                              <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                                {selectedAssetDetails.findings.map((f: any) => (
                                  <div
                                    key={f.id}
                                    className="p-2 bg-charcoal-dark border border-silver-bright/5 hover:border-silver-bright/20 flex items-center justify-between text-xs transition-colors"
                                  >
                                    <span className="text-silver-bright font-black truncate max-w-[200px]" title={f.title}>
                                      {f.title}
                                    </span>
                                    <span className={`text-[8px] font-black px-1.5 py-0.5 border ${
                                      f.severity === 'critical' || f.severity === 'high'
                                        ? 'text-rag-red border-rag-red/25 bg-rag-red/10'
                                        : f.severity === 'medium'
                                          ? 'text-rag-amber border-rag-amber/25 bg-rag-amber/10'
                                          : 'text-silver border-silver/20 bg-silver/5'
                                    }`}>
                                      {f.severity.toUpperCase()}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Linked Tasks */}
                          <div>
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-silver/45 mb-2 flex justify-between">
                              <span>Associated Scans</span>
                              <span>({selectedAssetDetails.tasks?.length || 0})</span>
                            </h3>
                            {(!selectedAssetDetails.tasks || selectedAssetDetails.tasks.length === 0) ? (
                              <p className="text-[10px] uppercase text-silver/30 italic">No scan tasks recorded.</p>
                            ) : (
                              <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                                {selectedAssetDetails.tasks.map((t: any) => (
                                  <Link
                                    key={t.id}
                                    to={routePath.task(t.id)}
                                    className="block p-2 bg-charcoal-dark border border-silver-bright/5 hover:border-silver-bright/25 flex justify-between items-center text-xs transition-colors group"
                                  >
                                    <span className="text-silver-bright group-hover:text-white font-bold uppercase truncate">
                                      {t.tool_name}
                                    </span>
                                    <span className="text-[10px] text-silver/40">
                                      {t.status.toUpperCase()}
                                    </span>
                                  </Link>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                    </motion.div>
                  ) : null
                ) : (
                  <motion.div
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="px-6 py-24 text-center space-y-3"
                  >
                    <p className="text-2xl font-black uppercase tracking-[0.22em] text-silver/20 italic">Inventory Idle</p>
                    <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-silver/15 max-w-[280px] mx-auto leading-relaxed">
                      Select an asset row or graph node to inspect relationships, severity profile, and scan lineage.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

            </div>
          </aside>

        </div>

      </div>
    </div>
  )
}
