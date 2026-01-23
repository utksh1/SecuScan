import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { scanTools, getToolsByCategory, tabCategories, ScanTool } from '../data/scanTools'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: { 
    opacity: 1, 
    scale: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 200, damping: 20 }
  }
}

export default function Scanner() {
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState('quick-start')
    const [searchQuery, setSearchQuery] = useState('')

    const handleToolSelect = (tool: ScanTool) => {
        if (tool.disabled) return
        navigate(`/scans/${tool.id}`)
    }

    const filteredTools = scanTools.filter(t => {
        const matchesTab = activeTab === 'quick-start' ? t.category === 'quick-start' : (
            (activeTab === 'recon' && t.category === 'recon') ||
            (activeTab === 'vulnerability' && t.category === 'vulnerability') ||
            (activeTab === 'utility' && t.category === 'utility')
        )
        const matchesSearch = t.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            t.purpose.toLowerCase().includes(searchQuery.toLowerCase())
        return matchesTab && matchesSearch
    })

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            {/* Neo-Brutalist Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
                <div className="space-y-4">
                  <div className="bg-rag-red text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                    Strike_Toolkit v12
                  </div>
                  <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic">
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
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                   </div>
                </div>
            </header>

            {/* Tactical Navigation */}
            <nav className="flex flex-wrap gap-4">
                {tabCategories.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-8 py-4 text-[10px] font-black uppercase tracking-[0.3em] transition-all border-4 flex items-center gap-3 ${
                            activeTab === tab.id 
                            ? 'bg-rag-red text-black border-black shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] -translate-x-1 -translate-y-1' 
                            : 'bg-charcoal text-silver/40 border-black hover:border-silver-bright/20'
                        }`}
                    >
                        {tab.name}
                        {activeTab === tab.id && <span className="w-2 h-2 bg-black"></span>}
                    </button>
                ))}
            </nav>

            {/* Tools Grid Section */}
            <main>
                <AnimatePresence mode='wait'>
                    <motion.div 
                        key={activeTab}
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                        exit={{ opacity: 0, y: 20 }}
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8"
                    >
                        {filteredTools.map((tool) => (
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
                                        <div className={`px-2 py-0.5 text-[8px] font-black uppercase tracking-widest italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                                            tool.riskLevel === 'aggressive' ? 'bg-rag-red text-black' : 
                                            tool.riskLevel === 'active' ? 'bg-rag-amber text-black' : 
                                            'bg-rag-green text-black'
                                        }`}>
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
                                        <div className="w-12 h-1 bg-silver-bright/10 mt-4 group-hover:w-full group-hover:bg-rag-red/30 transition-all duration-700"></div>
                                    </div>

                                    <p className="text-[10px] text-silver/40 uppercase tracking-widest leading-relaxed line-clamp-3 font-bold italic">
                                        {tool.purpose}
                                    </p>
                                </div>

                                <div className="pt-6 border-t-2 border-black border-dashed flex justify-between items-end">
                                    <span className="text-[9px] font-black text-silver-bright/20 uppercase tracking-[0.4em] group-hover:text-silver-bright transition-colors">INIT_DEPLOYMENT</span>
                                    <span className="material-symbols-outlined text-silver/20 group-hover:text-rag-red group-hover:translate-x-1 transition-all duration-300">double_arrow</span>
                                </div>

                                {tool.disabled && tool.disabledReason && (
                                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center p-8 text-center z-20">
                                        <span className="material-symbols-outlined text-rag-red text-3xl mb-4">lock_reset</span>
                                        <span className="text-[10px] text-rag-red font-black uppercase tracking-widest italic">{tool.disabledReason}</span>
                                    </div>
                                )}
                            </motion.button>
                        ))}

                        {/* Visual Balance Empty Blocks */}
                        {filteredTools.length > 0 && Array.from({ length: Math.max(0, 4 - (filteredTools.length % 4 || 4)) }).map((_, i) => (
                            <div key={i} className="bg-charcoal/30 border-4 border-black/5 border-dashed flex items-center justify-center opacity-10 p-10">
                                <span className="material-symbols-outlined text-4xl">add_box</span>
                            </div>
                        ))}
                    </motion.div>
                </AnimatePresence>
            </main>

            {/* Warning Section */}
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
