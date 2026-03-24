import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { scanTools, getToolsByCategory, getToolById, tabCategories, ScanTool } from '../data/scanTools'

export default function Scanner() {
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState('quick-start')
    const [searchQuery, setSearchQuery] = useState('')

    const handleToolSelect = (tool: ScanTool) => {
        if (tool.disabled) return
        navigate(`/scans/${tool.id}`)
    }

    const renderToolCard = (tool: ScanTool) => (
        <button
            key={tool.id}
            className={`p-10 bg-charcoal border border-accent-silver/10 hover:border-silver/40 transition-all text-left group relative flex flex-col justify-between h-72 rounded-sm shadow-2xl ${tool.disabled ? 'opacity-40 cursor-not-allowed grayscale' : 'cursor-pointer hover:bg-charcoal-light'}`}
            onClick={() => handleToolSelect(tool)}
            disabled={tool.disabled}
        >
            <div className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity bg-[radial-gradient(circle_at_center,_white_1px,_transparent_1px)] [background-size:20px_20px]"></div>
            
            <div className="space-y-6 relative z-10">
                <div className="flex justify-between items-start">
                    <span className={`text-[10px] font-bold uppercase tracking-[0.3em] italic px-3 py-1 border ${
                        tool.riskLevel === 'aggressive' ? 'text-rag-red border-rag-red/20 bg-rag-red/5' : 
                        tool.riskLevel === 'active' ? 'text-rag-amber border-rag-amber/20 bg-rag-amber/5' : 
                        'text-rag-green border-rag-green/20 bg-rag-green/5'
                    }`}>{tool.riskLevel} PROTOCOL</span>
                    {tool.presetCompatibility !== 'none' && (
                        <div className="flex items-center gap-2">
                             <span className="text-[8px] text-silver/20 font-bold uppercase tracking-widest hidden group-hover:block transition-all italic">COMPATIBLE</span>
                             <span className="material-symbols-outlined text-base text-silver/20 group-hover:text-silver-bright transition-colors">
                                {tool.presetCompatibility === 'quick-recon' ? 'bolt' : 'psychology'}
                             </span>
                        </div>
                    )}
                </div>
                <div>
                  <h3 className="text-2xl font-serif font-light text-silver-bright italic tracking-tight group-hover:underline underline-offset-8 decoration-silver/20 leading-snug">{tool.name}</h3>
                  <div className="h-0.5 w-12 bg-accent-silver/20 mt-4 group-hover:w-24 transition-all duration-500"></div>
                </div>
                <p className="text-[10px] text-silver/40 uppercase tracking-[0.1em] leading-relaxed line-clamp-3 italic font-medium">{tool.purpose}</p>
            </div>
            
            <div className="flex justify-between items-end opacity-20 group-hover:opacity-100 transition-all transform translate-y-2 group-hover:translate-y-0 relative z-10 pt-4 border-t border-accent-silver/5">
                <span className="text-[9px] font-bold text-silver-bright uppercase tracking-[0.5em]">Initialize Operation</span>
                <span className="material-symbols-outlined text-lg text-silver-bright translate-x-2 group-hover:translate-x-0 transition-transform">arrow_right_alt</span>
            </div>

            {tool.disabled && tool.disabledReason && (
                <div className="absolute inset-0 bg-charcoal-dark/90 flex flex-col items-center justify-center p-8 text-center backdrop-blur-[4px] z-20">
                    <span className="material-symbols-outlined text-rag-red/40 text-4xl mb-4">lock</span>
                    <span className="text-[10px] text-rag-red font-bold uppercase tracking-[0.4em] leading-loose italic">{tool.disabledReason}</span>
                </div>
            )}
        </button>
    )

    return (
        <div className="min-h-screen flex flex-col">
            <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10">
                <div className="flex items-center gap-8">
                    <div className="header-decoration hidden xl:block">
                        <span className="material-symbols-outlined text-accent-silver/30 text-4xl animate-pulse">radar</span>
                    </div>
                    <div>
                        <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">Operations Intelligence</h1>
                        <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">Surface Analysis • Reconnaissance Toolkit • DEPLOYMENT CENTER</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-12">
                   <div className="relative hidden xl:block">
                        <input
                            type="text"
                            placeholder="FILTER PROTOCOLS..."
                            className="bg-transparent border-b border-accent-silver/20 py-1 px-4 text-[10px] uppercase tracking-widest text-silver-bright focus:outline-none focus:border-silver-bright transition-colors w-72 placeholder:text-silver/10 italic"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <span className="absolute right-2 top-1 material-symbols-outlined text-sm text-silver/20">search</span>
                   </div>
                   <div className="text-right border-l border-accent-silver/10 pl-8">
                        <span className="text-[10px] font-medium text-silver/40 uppercase tracking-widest block mb-1">Active Agents</span>
                        <span className="text-xl font-light text-silver-bright font-mono italic">{scanTools.length.toString().padStart(3, '0')}</span>
                    </div>
                </div>
            </header>

            <main className="flex-1 p-12 space-y-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-1000">
                
                {/* Tactical Status Strip */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-px bg-accent-silver/10 executive-border overflow-hidden rounded-sm relative">
                    <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[radial-gradient(#3f3f46_1px,transparent_1px)] [background-size:24px_24px]"></div>
                    <div className="bg-charcoal p-8 flex items-center gap-6 group hover:bg-charcoal-light/50 transition-all">
                        <div className="w-12 h-12 flex items-center justify-center border border-rag-green/20 text-rag-green bg-rag-green/5 group-hover:scale-110 transition-transform">
                            <span className="material-symbols-outlined text-2xl">verified_user</span>
                        </div>
                        <div>
                            <span className="text-[9px] font-bold text-silver/30 uppercase tracking-[0.2em] italic block">Auth Status</span>
                            <span className="text-xs font-mono text-silver-bright uppercase">VERIFIED</span>
                        </div>
                    </div>
                    <div className="bg-charcoal p-8 flex items-center gap-6 group hover:bg-charcoal-light/50 transition-all">
                        <div className="w-12 h-12 flex items-center justify-center border border-accent-silver/20 text-silver/40 bg-white/5">
                            <span className="material-symbols-outlined text-2xl">security</span>
                        </div>
                        <div>
                            <span className="text-[9px] font-bold text-silver/30 uppercase tracking-[0.2em] italic block">Safe Mode</span>
                            <span className="text-xs font-mono text-rag-green/80 uppercase">ENABLED</span>
                        </div>
                    </div>
                    <div className="bg-charcoal p-8 flex items-center gap-6 group hover:bg-charcoal-light/50 transition-all">
                        <div className="w-12 h-12 flex items-center justify-center border border-accent-silver/20 text-silver/40 bg-white/5">
                            <span className="material-symbols-outlined text-2xl">dns</span>
                        </div>
                        <div>
                            <span className="text-[9px] font-bold text-silver/30 uppercase tracking-[0.2em] italic block">Compute Proxy</span>
                            <span className="text-xs font-mono text-silver-bright uppercase">LOCAL_CLUSTER</span>
                        </div>
                    </div>
                    <div className="bg-charcoal p-8 flex items-center gap-6 group hover:bg-charcoal-light/50 transition-all">
                        <div className="w-12 h-12 flex items-center justify-center border border-accent-silver/20 text-silver/40 bg-white/5">
                            <span className="material-symbols-outlined text-2xl">monitor_heart</span>
                        </div>
                        <div>
                            <span className="text-[9px] font-bold text-silver/30 uppercase tracking-[0.2em] italic block">Network Load</span>
                            <span className="text-xs font-mono text-silver-bright uppercase italic">OPTIMAL</span>
                        </div>
                    </div>
                </div>

                <nav className="flex gap-16 border-b border-accent-silver/10 pb-4">
                    {tabCategories.map(tab => (
                        <button
                            key={tab.id}
                            className={`text-[10px] font-bold uppercase tracking-[0.4em] transition-all relative pb-4 ${
                                activeTab === tab.id ? 'text-silver-bright italic scale-110' : 'text-silver/20 hover:text-silver/40'
                            }`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            {tab.name}
                            {activeTab === tab.id && (
                                <span className="absolute bottom-0 left-0 w-full h-px bg-silver-bright animate-in slide-in-from-left duration-700 shadow-[0_0_10px_white]"></span>
                            )}
                        </button>
                    ))}
                </nav>

                <div className="animate-in fade-in slide-in-from-bottom-8 duration-1000">
                    {activeTab === 'quick-start' ? (
                        <div className="space-y-12">
                            <div className="flex items-center gap-6">
                                <h3 className="text-xs font-bold uppercase tracking-[0.5em] text-silver/20 italic">Primary Deployment Agents</h3>
                                <div className="h-px flex-1 bg-accent-silver/5"></div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-px bg-accent-silver/5 executive-border overflow-hidden rounded-sm">
                                {getToolsByCategory('quick-start').map(renderToolCard)}
                                {/* Placeholder for visual balance if list is short */}
                                {[...Array(Math.max(0, 4 - getToolsByCategory('quick-start').length))].map((_, i) => (
                                    <div key={i} className="p-10 bg-charcoal/30 border border-dashed border-accent-silver/5 flex items-center justify-center grayscale opacity-10">
                                        <span className="material-symbols-outlined text-6xl">add</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-20">
                            {/* Generic category rendering with more density */}
                             <section className="space-y-12">
                                <div className="flex items-center gap-6">
                                    <h3 className="text-xs font-bold uppercase tracking-[0.5em] text-silver/20 italic">Operational Sub-Matrix</h3>
                                    <div className="h-px flex-1 bg-accent-silver/5"></div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-px bg-accent-silver/5 executive-border overflow-hidden rounded-sm">
                                    {scanTools.filter(t => 
                                        (activeTab === 'recon' && t.category === 'recon') ||
                                        (activeTab === 'vulnerability' && t.category === 'vulnerability') ||
                                        (activeTab === 'utility' && t.category === 'utility')
                                    ).map(renderToolCard)}
                                </div>
                            </section>
                        </div>
                    )}
                </div>

                {/* Tactical Footer / Disclaimer */}
                <div className="pt-20 opacity-20 hover:opacity-100 transition-opacity">
                    <div className="p-10 border border-dashed border-accent-silver/20 text-center space-y-4 rounded-sm">
                        <span className="material-symbols-outlined text-silver/20 text-4xl mb-4">gavel</span>
                        <p className="text-[10px] text-silver/60 uppercase tracking-[0.3em] font-light leading-loose max-w-4xl mx-auto">
                            The use of these tools is subject to active monitoring and strict operational engagement rules. Unauthorized utilization or escalation without valid mission authorization will result in immediate protocol revocation and administrative review.
                        </p>
                    </div>
                </div>
            </main>
        </div>
    )
}
