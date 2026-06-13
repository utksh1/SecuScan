import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listPlugins, PluginListItem } from '../api'
import { routePath } from '../routes'

// ─── Health state derivation ─────────────────────────────────────────────────

type HealthState = 'runnable' | 'degraded' | 'blocked'

function getHealthState(plugin: PluginListItem): HealthState {
  if (plugin.availability.runnable) return 'runnable'
  if (plugin.availability.missing_binaries && plugin.availability.missing_binaries.length > 0) {
    return 'degraded'
  }
  return 'blocked'
}

// ─── Style helpers ────────────────────────────────────────────────────────────

const stateConfig: Record<HealthState, {
  label: string
  color: string
  chip: string
  rail: string
  accent: string
  icon: string
  emptyText: string
}> = {
  runnable: {
    label: 'Runnable',
    color: 'bg-rag-green',
    chip: 'bg-rag-green text-black',
    rail: 'bg-rag-green',
    accent: 'text-rag-green',
    icon: 'check_circle',
    emptyText: 'No plugins are currently runnable.',
  },
  degraded: {
    label: 'Degraded',
    color: 'bg-rag-amber',
    chip: 'bg-rag-amber text-black',
    rail: 'bg-rag-amber',
    accent: 'text-rag-amber',
    icon: 'warning',
    emptyText: 'No plugins are in a degraded state.',
  },
  blocked: {
    label: 'Blocked',
    color: 'bg-rag-red',
    chip: 'bg-rag-red text-black',
    rail: 'bg-rag-red',
    accent: 'text-rag-red',
    icon: 'block',
    emptyText: 'No plugins are blocked.',
  },
}

// ─── Sub-components ──────────────────────────────────────────────────────────

interface PluginCardProps {
  plugin: PluginListItem
  state: HealthState
  onNavigate: () => void
}

function PluginCard({ plugin, state, onNavigate }: PluginCardProps) {
  const cfg = stateConfig[state]

  return (
    <button
      type="button"
      onClick={onNavigate}
      className="relative w-full text-left bg-charcoal border-4 border-black p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all group"
    >
      {/* State rail */}
      <span className={`absolute inset-y-0 left-0 w-1.5 ${cfg.rail}`} />

      <div className="pl-3 space-y-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.18em] border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${cfg.chip}`}>
                {cfg.label}
              </span>
              <span className="px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.18em] bg-charcoal-dark text-silver/60 border border-silver-bright/10">
                {plugin.category}
              </span>
              <span className="px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.18em] bg-charcoal-dark text-silver/60 border border-silver-bright/10">
                {plugin.safety_level}
              </span>
            </div>
            <h3 className="text-xl font-black uppercase tracking-tight text-silver-bright group-hover:text-rag-red transition-colors">
              {plugin.name}
            </h3>
          </div>
          <span className="material-symbols-outlined text-silver/20 group-hover:text-silver-bright transition-colors shrink-0">
            arrow_forward
          </span>
        </div>

        {/* Description */}
        {plugin.description && (
          <p className="text-sm text-silver/60 leading-relaxed line-clamp-2">{plugin.description}</p>
        )}

        {/* Missing binaries */}
        {plugin.availability.missing_binaries && plugin.availability.missing_binaries.length > 0 && (
          <div className="space-y-1">
            <p className="text-[9px] font-black uppercase tracking-[0.2em] text-rag-amber">
              Missing Dependencies
            </p>
            <div className="flex flex-wrap gap-2">
              {plugin.availability.missing_binaries.map((bin) => (
                <span
                  key={bin}
                  className="px-2 py-1 text-[10px] font-mono bg-rag-amber/10 border border-rag-amber/30 text-rag-amber"
                >
                  {bin}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Guidance */}
        {plugin.availability.guidance && (
          <div className="border-l-4 border-rag-blue bg-rag-blue/5 px-3 py-2">
            <p className="text-[11px] font-mono text-silver/70 leading-relaxed">
              {plugin.availability.guidance}
            </p>
          </div>
        )}

        {/* Status message if no binaries/guidance but still not runnable */}
        {!plugin.availability.runnable &&
          !plugin.availability.guidance &&
          (!plugin.availability.missing_binaries || plugin.availability.missing_binaries.length === 0) && (
            <div className="border-l-4 border-rag-red bg-rag-red/5 px-3 py-2">
              <p className="text-[11px] font-mono text-rag-red/80 leading-relaxed uppercase tracking-widest">
                {plugin.availability.status || 'Capability denied or blocked by operator policy'}
              </p>
            </div>
          )}
      </div>
    </button>
  )
}

interface HealthGroupProps {
  state: HealthState
  plugins: PluginListItem[]
  onNavigate: (pluginId: string) => void
}

function HealthGroup({ state, plugins, onNavigate }: HealthGroupProps) {
  const cfg = stateConfig[state]

  return (
    <section>
      {/* Group header */}
      <div className="flex items-center gap-4 border-b-4 border-black pb-4 mb-6">
        <span className={`material-symbols-outlined text-2xl ${cfg.accent}`}>{cfg.icon}</span>
        <div>
          <h2 className={`text-2xl font-black uppercase tracking-[0.12em] ${cfg.accent}`}>
            {cfg.label}
          </h2>
          <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest">
            {plugins.length} plugin{plugins.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className={`ml-auto px-4 py-2 text-xl font-black text-black ${cfg.color} border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]`}>
          {plugins.length}
        </div>
      </div>

      {/* Plugin cards */}
      {plugins.length === 0 ? (
        <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/30 py-12 text-center">
          <p className="text-sm font-mono uppercase tracking-widest text-silver/20">{cfg.emptyText}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {plugins.map((plugin) => (
            <PluginCard
              key={plugin.id}
              plugin={plugin}
              state={state}
              onNavigate={() => onNavigate(plugin.id)}
            />
          ))}
        </div>
      )}
    </section>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function PluginHealth() {
  const navigate = useNavigate()
  const [plugins, setPlugins] = useState<PluginListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function fetchPlugins() {
    setLoading(true)
    setError(null)
    listPlugins()
      .then((data) => setPlugins(data.plugins || []))
      .catch(() => setError('Failed to load plugin health data.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchPlugins()
  }, [])

  const grouped = {
    runnable: plugins.filter((p) => getHealthState(p) === 'runnable'),
    degraded: plugins.filter((p) => getHealthState(p) === 'degraded'),
    blocked: plugins.filter((p) => getHealthState(p) === 'blocked'),
  }

  function handleNavigate(pluginId: string) {
    navigate(routePath.scanTool(pluginId))
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver px-4 py-6 md:px-8 md:py-10">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-12">

        {/* Header */}
        <header className="border-b-4 border-silver-bright/10 pb-8">
          <div className="mb-4 inline-block bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Plugin_Registry_v1.0
          </div>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="space-y-3">
              <h1 className="text-5xl font-black uppercase tracking-tighter text-silver-bright italic md:text-7xl">
                Plugin{' '}
                <span
                  className="text-transparent"
                  style={{ WebkitTextStroke: '1px var(--accent-silver-bright)' }}
                >
                  Health
                </span>
              </h1>
              <p className="text-xs font-mono uppercase tracking-[0.24em] text-silver/45">
                Operational visibility // {plugins.length} total plugins registered
              </p>
            </div>

            {/* Summary metrics */}
            <div className="grid w-full gap-3 sm:grid-cols-3 xl:w-auto">
              {(['runnable', 'degraded', 'blocked'] as HealthState[]).map((state) => {
                const cfg = stateConfig[state]
                return (
                  <div
                    key={state}
                    className="border-2 border-black bg-charcoal px-4 py-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]"
                  >
                    <p className="mb-2 text-[10px] font-black uppercase tracking-[0.25em] text-silver/55">
                      {cfg.label}
                    </p>
                    <p className={`text-3xl font-black italic tracking-tight ${cfg.accent}`}>
                      {String(grouped[state].length).padStart(2, '0')}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Refresh button */}
          <div className="mt-6">
            <button
              type="button"
              onClick={fetchPlugins}
              disabled={loading}
              className="border-2 border-black bg-charcoal px-6 py-3 text-[10px] font-black uppercase tracking-widest text-silver-bright shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all disabled:opacity-40 flex items-center gap-2"
              title="Refresh plugin health"
            >
              <span className={`material-symbols-outlined text-sm ${loading ? 'animate-spin' : ''}`}>
                sync
              </span>
              Refresh
            </button>
          </div>
        </header>

        {/* Loading */}
        {loading && (
          <div className="border-4 border-dashed border-silver-bright/10 bg-charcoal/40 py-24 text-center">
            <p className="text-sm font-mono uppercase tracking-[0.25em] text-silver/50 animate-pulse">
              Scanning plugin registry...
            </p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="border-4 border-rag-red bg-rag-red/10 p-8 flex items-center gap-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
            <span className="material-symbols-outlined text-rag-red text-3xl">error</span>
            <div className="space-y-1">
              <p className="text-xs font-black text-rag-red uppercase tracking-widest">
                Plugin_Registry_Retrieval_Failed
              </p>
              <p className="text-[10px] font-mono text-silver/40 uppercase tracking-widest">{error}</p>
            </div>
            <button
              onClick={fetchPlugins}
              className="ml-auto bg-rag-red border-4 border-black px-6 py-3 text-[9px] font-black uppercase tracking-widest text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
            >
              Retry
            </button>
          </div>
        )}

        {/* Health groups */}
        {!loading && !error && (
          <div className="space-y-16">
            {(['blocked', 'degraded', 'runnable'] as HealthState[]).map((state) => (
              <HealthGroup
                key={state}
                state={state}
                plugins={grouped[state]}
                onNavigate={handleNavigate}
              />
            ))}
          </div>
        )}

      </div>
    </div>
  )
}
