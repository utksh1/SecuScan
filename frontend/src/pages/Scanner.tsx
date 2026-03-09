import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { listPlugins, PluginListItem } from '../api'
import { scanTools } from '../data/scanTools'
import { routePath } from '../routes'

type RiskLevel = 'passive' | 'active' | 'aggressive'
type PresetCompatibility = 'quick-recon' | 'deep-scan' | 'both' | 'none'

interface CatalogTool {
  id: string
  name: string
  purpose: string
  riskLevel: RiskLevel
  presetCompatibility: PresetCompatibility
  requiresConsent: boolean
  category: string
  disabled: boolean
  disabledReason?: string
  isPlugin: boolean
  availability?: PluginListItem['availability']
}

const LEGACY_TAB_ORDER = ['quick-start', 'recon', 'vulnerability', 'exploit', 'utils', 'robots'] as const

const LEGACY_TAB_LABELS: Record<string, string> = {
  'quick-start': 'Quick Start',
  recon: 'Recon Tools',
  vulnerability: 'Vulnerability Scanners',
  exploit: 'Exploit Detection',
  utils: 'Utils',
  robots: 'Robots',
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 200, damping: 20 },
  },
}

function mapSafetyToRiskLevel(safetyLevel: string): RiskLevel {
  if (safetyLevel === 'exploit') return 'aggressive'
  if (safetyLevel === 'intrusive') return 'active'
  return 'passive'
}

function normalizeCategoryId(raw: string): string {
  return raw.trim().toLowerCase().replace(/\s+/g, '-')
}

function formatCategoryLabel(category: string): string {
  if (LEGACY_TAB_LABELS[category]) return LEGACY_TAB_LABELS[category]
  return category
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function mapPluginCategoryToLegacyTab(category: string): string {
  switch (category) {
    case 'vulnerability':
    case 'code':
      return 'vulnerability'
    case 'execution':
    case 'exploit':
      return 'exploit'
    case 'utils':
      return 'utils'
    default:
      return 'recon'
  }
}

function mapPluginToCatalogTool(plugin: PluginListItem): CatalogTool {
  const normalizedCategory = normalizeCategoryId(plugin.category)
  return {
    id: plugin.id,
    name: plugin.name,
    purpose: plugin.description,
    riskLevel: mapSafetyToRiskLevel(plugin.safety_level),
    presetCompatibility: 'both',
    requiresConsent: plugin.requires_consent,
    category: mapPluginCategoryToLegacyTab(normalizedCategory),
    disabled: false,
    isPlugin: true,
    availability: plugin.availability,
  }
}

function mapLegacyToolsToCatalogTools(existingPluginIds: Set<string>): CatalogTool[] {
  return scanTools
    .filter((tool) => !existingPluginIds.has(tool.id))
    .map((tool) => ({
      id: tool.id,
      name: tool.name,
      purpose: tool.purpose,
      riskLevel: tool.riskLevel,
      presetCompatibility: tool.presetCompatibility,
      requiresConsent: tool.requiresConsent,
      category: normalizeCategoryId(tool.category),
      disabled: true,
      disabledReason: tool.disabledReason || 'Backend plugin pending',
      isPlugin: false,
    }))
}

export default function Scanner() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [tools, setTools] = useState<CatalogTool[]>([])
  const [tabOrder, setTabOrder] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadCatalog() {
      try {
        const response = await listPlugins()
        if (cancelled) return

        const pluginTools = response.plugins.map(mapPluginToCatalogTool)
        const pluginIds = new Set(pluginTools.map((tool) => tool.id))
        const legacyTools = mapLegacyToolsToCatalogTools(pluginIds)
        const mergedTools = [...pluginTools, ...legacyTools]
        const mergedCategories = [...LEGACY_TAB_ORDER]
        for (const category of legacyTools.map((tool) => tool.category)) {
          if (!mergedCategories.includes(category)) mergedCategories.push(category)
        }

        setTools(mergedTools)
        setTabOrder(mergedCategories)
        setLoadError(null)
      } catch (error) {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : 'Failed to load plugin catalog')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadCatalog()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (tabOrder.length > 0 && !tabOrder.includes(activeTab)) {
      setActiveTab(tabOrder[0])
    }
  }, [tabOrder, activeTab])

  const categoryToolsCount = useMemo(
    () => tools.filter((tool) => tool.category === activeTab).length,
    [tools, activeTab],
  )

  const filteredTools = useMemo(() => {
    const query = searchQuery.toLowerCase().trim()
    return tools.filter((tool) => {
      if (tool.category !== activeTab) return false
      if (!query) return true
      return tool.name.toLowerCase().includes(query) || tool.purpose.toLowerCase().includes(query)
    })
  }, [tools, activeTab, searchQuery])

  const handleToolSelect = (tool: CatalogTool) => {
    if (tool.disabled) return
    navigate(routePath.scanTool(tool.id))
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
        <div className="space-y-4">
          <div className="bg-rag-red text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Strike_Toolkit v12
          </div>
          <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic whitespace-nowrap">
            Combat <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Scanner</span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
            SELECT_TOOL_PROTOCOL // DEPLOY_PAYLOAD // MONITOR_FEED
          </p>
        </div>

        <div className="flex items-center gap-6">
          <div className="relative group">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-silver/20 group-focus-within:text-rag-red transition-colors text-sm">search</span>
            <input
              type="text"
              placeholder="SEARCH_PROTOCOLS..."
              className="bg-charcoal border-4 border-black pl-12 pr-4 py-4 text-xs font-black uppercase tracking-widest text-silver-bright focus:outline-none focus:border-rag-red transition-all w-80 placeholder:text-silver/10 italic shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>
        </div>
      </header>

      {loadError && (
        <section className="bg-charcoal border-4 border-rag-red p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-rag-red">Catalog load failed</p>
          <p className="text-[10px] text-silver/60 uppercase tracking-widest mt-3">{loadError}</p>
        </section>
      )}

      <nav className="flex flex-wrap gap-4">
        {tabOrder.map((category) => (
          <button
            key={category}
            onClick={() => setActiveTab(category)}
            className={`px-8 py-4 text-[10px] font-black uppercase tracking-[0.3em] transition-all border-4 flex items-center gap-3 ${
              activeTab === category
                ? 'bg-rag-red text-black border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] -translate-x-1 -translate-y-1'
                : 'bg-charcoal text-silver/40 border-black hover:border-silver-bright/20'
            }`}
          >
            {formatCategoryLabel(category)}
            {activeTab === category && <span className="w-2 h-2 bg-black" />}
          </button>
        ))}
      </nav>

      <main>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab || 'loading'}
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            exit={{ opacity: 0, y: 20 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8"
          >
            {!loading &&
              filteredTools.map((tool) => (
                <motion.button
                  key={tool.id}
                  variants={itemVariants}
                  disabled={tool.disabled}
                  onClick={() => handleToolSelect(tool)}
                  className={`group relative p-8 bg-charcoal border-4 border-black text-left flex flex-col justify-between h-80 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] transition-all overflow-hidden ${
                    tool.disabled
                      ? 'opacity-30 cursor-not-allowed grayscale'
                      : 'hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] hover:-translate-x-1 hover:-translate-y-1'
                  }`}
                >
                  <div className="space-y-6 relative z-10">
                    <div className="flex justify-between items-start">
                      <div
                        className={`px-2 py-0.5 text-[8px] font-black uppercase tracking-widest italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                          tool.riskLevel === 'aggressive'
                            ? 'bg-rag-red text-black'
                            : tool.riskLevel === 'active'
                              ? 'bg-rag-amber text-black'
                              : 'bg-rag-green text-black'
                        }`}
                      >
                        {tool.riskLevel}_STRIKE
                      </div>
                      <span className="material-symbols-outlined text-silver/10 group-hover:text-silver-bright transition-colors duration-500">
                        {tool.presetCompatibility === 'quick-recon' ? 'bolt' : 'psychology'}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-3xl font-black text-silver-bright uppercase tracking-tighter italic leading-none group-hover:text-rag-red transition-colors">
                        {tool.name}
                      </h3>
                      <div className="w-12 h-1 bg-silver-bright/10 mt-4 group-hover:w-full group-hover:bg-rag-red/30 transition-all duration-700" />
                    </div>

                    <p className="text-[10px] text-silver/40 uppercase tracking-widest leading-relaxed line-clamp-3 font-bold italic">
                      {tool.purpose}
                    </p>

                    {tool.isPlugin && tool.availability && tool.availability.missing_binaries.length > 0 && (
                      <div className="text-[9px] uppercase tracking-widest text-rag-amber font-black">
                        Missing: {tool.availability.missing_binaries.join(', ')}
                      </div>
                    )}
                  </div>

                  <div className="pt-6 border-t-2 border-black border-dashed flex justify-between items-end">
                    <span className="text-[9px] font-black text-silver-bright/20 uppercase tracking-[0.4em] group-hover:text-silver-bright transition-colors">
                      INIT_DEPLOYMENT
                    </span>
                    <span className="material-symbols-outlined text-silver/20 group-hover:text-rag-red group-hover:translate-x-1 transition-all duration-300">
                      double_arrow
                    </span>
                  </div>

                  {tool.disabled && tool.disabledReason && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center p-8 text-center z-20">
                      <span className="material-symbols-outlined text-rag-red text-3xl mb-4">lock_reset</span>
                      <span className="text-[10px] text-rag-red font-black uppercase tracking-widest italic">{tool.disabledReason}</span>
                    </div>
                  )}
                </motion.button>
              ))}

            {!loading && filteredTools.length === 0 && (
              <motion.div
                variants={itemVariants}
                className="md:col-span-2 xl:col-span-4 bg-charcoal border-4 border-black p-10 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]"
              >
                <div className="space-y-6">
                  {searchQuery.trim().length > 0 ? (
                    <>
                      <div className="text-[10px] font-black uppercase tracking-[0.3em] text-rag-amber">No tools match search</div>
                      <p className="text-[10px] text-silver/60 uppercase tracking-widest leading-relaxed">
                        No tools in this category match the current query.
                      </p>
                      <button
                        onClick={() => setSearchQuery('')}
                        className="px-6 py-3 text-[10px] font-black uppercase tracking-[0.3em] bg-rag-blue text-black border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
                      >
                        Clear Search
                      </button>
                    </>
                  ) : categoryToolsCount === 0 ? (
                    <>
                      <div className="text-[10px] font-black uppercase tracking-[0.3em] text-rag-amber">No tools available in this category</div>
                      <p className="text-[10px] text-silver/60 uppercase tracking-widest leading-relaxed">
                        This category currently has no active tools. Use the first available category to continue.
                      </p>
                      <button
                        onClick={() => {
                          if (tabOrder.length > 0) setActiveTab(tabOrder[0])
                        }}
                        className="px-6 py-3 text-[10px] font-black uppercase tracking-[0.3em] bg-silver-bright text-black border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
                      >
                        Go to Quick Start
                      </button>
                    </>
                  ) : null}
                </div>
              </motion.div>
            )}

            {!loading &&
              filteredTools.length > 0 &&
              Array.from({ length: Math.max(0, 4 - (filteredTools.length % 4 || 4)) }).map((_, index) => (
                <div key={index} className="bg-charcoal/30 border-4 border-black/5 border-dashed flex items-center justify-center opacity-10 p-10">
                  <span className="material-symbols-outlined text-4xl">add_box</span>
                </div>
              ))}
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="pt-24 opacity-20 hover:opacity-100 transition-opacity duration-700 pointer-events-none md:pointer-events-auto">
        <div className="p-12 border-4 border-black border-dashed flex flex-col md:flex-row items-center gap-10 bg-charcoal/50">
          <span className="material-symbols-outlined text-rag-red text-6xl">gavel</span>
          <div className="space-y-4">
            <p className="text-xs font-black text-rag-amber uppercase tracking-[0.4em] italic leading-relaxed">
              UNAUTHORIZED_DEPLOYMENT_IS_MONITORED
            </p>
            <p className="text-[10px] text-silver/40 uppercase tracking-widest font-bold leading-loose max-w-4xl">
              Operation engagement rules strictly apply. By initializing any protocol, you acknowledge the jurisdiction of the Secure Enclave and provide full consent for activity recording and auditing. Escalate only under valid mission authorization.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
