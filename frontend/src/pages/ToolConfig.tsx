import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getToolById, ScanTool } from '../data/scanTools'
import { useToast } from '../components/ToastContext'
import { startTask } from '../api'

type ScanMode = 'light' | 'deep' | 'custom'

export default function ToolConfig() {
    const { toolId } = useParams<{ toolId: string }>()
    const navigate = useNavigate()
    const { addToast } = useToast()
    const [tool, setTool] = useState<ScanTool | null>(null)
    const [submitting, setSubmitting] = useState(false)
    const [scanMode, setScanMode] = useState<ScanMode>('light')
    const [target, setTarget] = useState('')
    const [consentGranted, setConsentGranted] = useState(false)

    // -- Common / Advanced --
    const [showExpertMode, setShowExpertMode] = useState(false)
    const [rawFlags, setRawFlags] = useState('')
    const [followRedirects, setFollowRedirects] = useState(true)
    const [userAgent, setUserAgent] = useState('SecuScan/1.0')
    const [requestTimeout, setRequestTimeout] = useState(30)
    const [requestRate, setRequestRate] = useState(10)

    // -- Network Scanner --
    const [networkProtocol, setNetworkProtocol] = useState('TCP')
    const [portSelection, setPortSelection] = useState('common')
    const [customPorts, setCustomPorts] = useState('')
    const [networkScanOptions, setNetworkScanOptions] = useState({
        checkAlive: true,
        skipDiscovery: false,
        resolveNames: true
    })
    const [enumerationSuite, setEnumerationSuite] = useState({
        serviceVersion: true,
        osDetection: false,
        defaultScripts: true
    })
    const [timingTemplate, setTimingTemplate] = useState('T3')
    const [retries, setRetries] = useState(2)

    // -- Website Scanner --
    const [crawlDepth, setCrawlDepth] = useState(2)
    const [maxPages, setMaxPages] = useState(100)
    const [websiteScope, setWebsiteScope] = useState({
        sameDomain: true,
        includeSubdomains: false,
        includeQueryParams: true
    })
    const [webChecks, setWebChecks] = useState({
        securityHeaders: true,
        tlsConfig: true,
        serverMisconfig: true,
        fingerprinting: true,
        cmsDetection: true
    })
    const [vulnDetection, setVulnDetection] = useState({
        sqli: true,
        xss: true,
        openRedirect: true,
        fileInclusion: true
    })

    // -- URL Fuzzer --
    const [fuzzMode, setFuzzMode] = useState('directory')
    const [wordlist, setWordlist] = useState('common')
    const [statusCodes, setStatusCodes] = useState('200,204,301,302,307,401,403')
    const [excludeSize, setExcludeSize] = useState('')
    const [threads, setThreads] = useState(10)
    const [httpMethod, setHttpMethod] = useState('GET')
    const [extensions, setExtensions] = useState('php,html,txt')

    // -- API Scanner --
    const [apiType, setApiType] = useState('rest')
    const [authMethod, setAuthMethod] = useState('none')
    const [authToken, setAuthToken] = useState('')
    const [endpointDiscovery, setEndpointDiscovery] = useState('auto')
    const [apiChecks, setApiChecks] = useState({
        missingAuth: true,
        improperAuthz: true,
        methodExposure: true,
        massAssignment: true
    })
    const [concurrency, setConcurrency] = useState(5)

    // -- SSL/TLS Scanner --
    const [tlsPort, setTlsPort] = useState('443')
    const [tlsProtocol, setTlsProtocol] = useState('HTTPS')
    const [certChecks, setCertChecks] = useState({
        validity: true,
        expiration: true,
        chain: true
    })
    const [protocolChecks, setProtocolChecks] = useState({
        versions: true,
        weakCiphers: true,
        forwardSecrecy: true
    })
    const [tlsAudit, setTlsAudit] = useState({
        renegotiation: true,
        compression: true,
        misconfigs: true
    })

    // -- Website Recon --
    const [reconModules, setReconModules] = useState({
        headers: true,
        fingerprinting: true,
        metadata: true,
        banner: true,
        robots: true
    })
    const [dnsHosting, setDnsHosting] = useState({
        dnsRecords: true,
        ipHosting: true,
        cdn: true
    })
    const [outputPrefs, setOutputPrefs] = useState({
        groupByCategory: true,
        highlightUncommon: true,
        normalizeTech: true
    })

    // -- Subdomain Finder --
    const [discoveryMethods, setDiscoveryMethods] = useState({
        passive: true,
        brute: false,
        structured: true
    })
    const [aliveCheck, setAliveCheck] = useState(true)

    // -- SQLi / XSS --
    const [targetParams, setTargetParams] = useState('all')
    const [detectionLevel, setDetectionLevel] = useState(3)
    const [dbHint, setDbHint] = useState('auto')
    const [xssPayloadSet, setXssPayloadSet] = useState('standard')

    // -- Secret Scanner --
    const [secretScope, setSecretScope] = useState('recursive')
    const [secretTypes, setSecretTypes] = useState('all')
    const [filePatterns, setFilePatterns] = useState('.env, config.*, *.json')

    useEffect(() => {
        if (toolId) {
            const foundTool = getToolById(toolId)
            if (foundTool) {
                setTool(foundTool)
            } else {
                navigate('/scanner')
            }
        }
    }, [toolId, navigate])

    if (!tool) return null

    const isNetworkScanner = tool.id.includes('network-scanner')
    const isWebsiteScanner = tool.id.includes('website-scanner')
    const isFuzzer = tool.id.includes('url-fuzzer')
    const isApiScanner = tool.id.includes('api-scanner')
    const isTlsScanner = tool.id === 'ssl-tls-scanner'
    const isWebRecon = tool.id === 'website-recon' || tool.id === 'website-recon-2'
    const isSubdomainFinder = tool.id === 'subdomain-finder'
    const isSqli = tool.id === 'sqli-detection'
    const isXss = tool.id === 'xss-detection'
    const isSecretScanner = tool.id === 'secret-scanner'
    const isUtils = tool.category === 'utils'

    const targetHasPlaceholder = target.includes('FUZZ') || target.includes('WORD')
    const isTargetValid = isFuzzer ? targetHasPlaceholder : target.length > 2

    const resolvePluginId = (toolId: string) => {
        if (toolId.includes('network') || toolId === 'port-scanner') return 'nmap'
        if (toolId.includes('tls') || toolId.includes('ssl')) return 'tls_inspector'
        if (toolId.includes('fuzzer')) return 'dir_discovery'
        if (toolId.includes('website') || toolId.includes('recon') || toolId.includes('http')) return 'http_inspector'
        if (toolId.includes('sqli')) return 'sqlmap'
        if (toolId.includes('api') || toolId.includes('wordpress') || toolId.includes('drupal') || toolId.includes('joomla') || toolId.includes('sharepoint') || toolId.includes('secret')) return 'nikto'
        return null
    }

    const buildInputs = () => {
        const pluginId = resolvePluginId(tool.id)
        if (pluginId === 'nmap') {
            return {
                target,
                safe_mode: scanMode !== 'deep',
                scan_type: networkProtocol === 'UDP' ? 'U' : 'T',
                service_detection: enumerationSuite.serviceVersion,
                os_detection: enumerationSuite.osDetection,
                ports: portSelection === 'custom' ? customPorts : '',
            }
        }
        if (pluginId === 'tls_inspector') {
            return {
                host: `${target}${tlsPort ? `:${tlsPort}` : ''}`,
                show_chain: certChecks.chain,
                timeout: requestTimeout,
            }
        }
        if (pluginId === 'dir_discovery') {
            return {
                url: target,
                threads,
                extensions,
                wordlist,
            }
        }
        if (pluginId === 'sqlmap') {
            return {
                url: target,
                level: detectionLevel,
            }
        }
        if (pluginId === 'nikto') {
            return {
                target,
                timeout: requestTimeout,
            }
        }
        return {
            url: target,
            follow_redirects: followRedirects,
            timeout: requestTimeout,
        }
    }

    const resolvePreset = (pluginId: string) => {
        if (pluginId === 'http_inspector') return scanMode === 'deep' ? 'full' : 'quick'
        if (pluginId === 'nmap') return scanMode === 'deep' ? 'comprehensive' : 'quick'
        return undefined
    }

    const handleStartScan = async () => {
        if (!isTargetValid || (tool.requiresConsent && !consentGranted) || submitting) return

        const pluginId = resolvePluginId(tool.id)
        if (!pluginId) {
            addToast(`No backend plugin is mapped for ${tool.name}.`, 'error')
            return
        }

        try {
            setSubmitting(true)
            const task = await startTask(
                pluginId,
                buildInputs(),
                tool.requiresConsent ? consentGranted : true,
                resolvePreset(pluginId)
            )
            addToast(`Task queued: ${tool.name}`, 'success')
            navigate(`/task/${task.task_id}`)
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Failed to start scan'
            addToast(message, 'error')
        } finally {
            setSubmitting(false)
        }
    }

    const getRiskBadgeColor = (risk: string) => {
        switch (risk) {
            case 'passive': return 'text-rag-blue border-rag-blue/20'
            case 'active': return 'text-rag-amber border-rag-amber/20'
            case 'aggressive': return 'text-rag-red border-rag-red/20'
            default: return 'text-silver/40 border-accent-silver/10'
        }
    }

    let sectionCounter = 1;
    const nextNum = () => sectionCounter++.toString().padStart(2, '0');

    return (
        <div className="min-h-screen flex flex-col scale-in-center">
            {/* Header */}
            <header className="w-full px-12 py-10 flex justify-between items-center border-b border-accent-silver/10 bg-charcoal-dark/50 backdrop-blur-md sticky top-0 z-40">
                <div className="flex items-center gap-8">
                    <button 
                        className="w-12 h-12 flex items-center justify-center border border-accent-silver/20 hover:border-silver/40 text-silver/40 hover:text-white transition-all rounded-sm group relative"
                        onClick={() => navigate('/scanner')}
                    >
                        <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <span className="material-symbols-outlined text-sm relative z-10">arrow_back</span>
                    </button>
                    <div>
                        <h1 className="text-3xl font-serif font-light text-silver-bright tracking-tight italic uppercase leading-none">{tool.name}</h1>
                        <p className="text-[10px] font-light text-silver/40 uppercase tracking-[0.4em] mt-3 italic">{tool.purpose}</p>
                    </div>
                </div>
            </header>

            <main className="flex-1 p-12 max-w-[1600px] mx-auto w-full animate-in fade-in duration-700">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
                    
                    {/* Left Column: Form Fields */}
                    <div className="lg:col-span-3 space-y-12">
                        
                        {/* 01. Target Section */}
                        <section className="space-y-8">
                            <div className="flex items-baseline gap-6">
                                <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic">{nextNum()}. Target_Configuration</h3>
                                <div className="flex-1 h-px bg-accent-silver/10"></div>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                                <div className="md:col-span-3 space-y-4">
                                    <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">
                                        Interface_Endpoint <span className="text-rag-blue/60">[Required]</span>
                                    </label>
                                    <div className="relative group">
                                        <input
                                            type="text"
                                            className={`w-full bg-charcoal border border-accent-silver/10 p-6 font-mono text-sm text-silver-bright focus:outline-none focus:border-silver/40 transition-all placeholder:text-silver/10 italic ${
                                                (isFuzzer && !targetHasPlaceholder && target.length > 0) ? 'border-rag-red/40 text-rag-red' : ''
                                            }`}
                                            placeholder={isFuzzer ? 'e.g. https://api.com/FUZZ' : (isSubdomainFinder ? 'e.g. example.com' : 'e.g. https://example.com')}
                                            value={target}
                                            onChange={(e) => setTarget(e.target.value)}
                                        />
                                        <div className="absolute right-6 top-1/2 -translate-y-1/2 flex gap-4 opacity-10 group-focus-within:opacity-40 transition-opacity">
                                            <span className="material-symbols-outlined text-sm">terminal</span>
                                            <span className="material-symbols-outlined text-sm">wifi_tethering</span>
                                        </div>
                                    </div>
                                    {(isWebsiteScanner || isFuzzer || isWebRecon || isApiScanner || isXss || isSqli) && (
                                        <label className="flex items-center gap-4 cursor-pointer group w-fit ml-1 pt-2">
                                            <div className="relative w-4 h-4 border border-accent-silver/20 rounded-sm flex items-center justify-center transition-all group-hover:border-silver/40">
                                                <input 
                                                    type="checkbox" 
                                                    className="hidden peer"
                                                    checked={followRedirects} 
                                                    onChange={(e) => setFollowRedirects(e.target.checked)} 
                                                />
                                                <div className="w-1.5 h-1.5 bg-silver opacity-0 peer-checked:opacity-100 transition-opacity shadow-[0_0_8px_white]"></div>
                                            </div>
                                            <span className="text-[10px] uppercase font-bold tracking-widest text-silver/30 group-hover:text-silver/60 transition-colors italic">Follow_30X_Redirects</span>
                                        </label>
                                    )}
                                </div>
                                {isTlsScanner && (
                                    <div className="space-y-4">
                                        <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">Port_Symmetry</label>
                                        <input type="text" className="w-full bg-charcoal border border-accent-silver/10 p-6 font-mono text-sm text-silver-bright focus:outline-none focus:border-silver/40 transition-all text-center italic" value={tlsPort} onChange={(e) => setTlsPort(e.target.value)} />
                                    </div>
                                )}
                            </div>
                        </section>

                        {/* 02. Scan Presets */}
                        {!isWebRecon && !isUtils && !isSecretScanner && (
                            <section className="space-y-8">
                                <div className="flex items-baseline gap-6">
                                    <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic">{nextNum()}. Protocol_Modes</h3>
                                    <div className="flex-1 h-px bg-accent-silver/10"></div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-1">
                                    {[
                                        { id: 'light', label: 'Passive_Stealth', desc: 'Minimal footprint, safe defaults.' },
                                        { id: 'deep', label: 'Active_Infiltration', desc: 'Comprehensive coverage, heavy traffic.' },
                                        { id: 'custom', label: 'Tactical_Override', desc: 'Full manual parameter control.' }
                                    ].map(mode => (
                                        <button 
                                            key={mode.id}
                                            className={`p-8 border border-accent-silver/10 transition-all text-left flex flex-col gap-4 relative overflow-hidden group ${
                                                scanMode === mode.id ? 'bg-charcoal-light border-silver/20' : 'bg-charcoal hover:bg-charcoal/80'
                                            }`}
                                            onClick={() => setScanMode(mode.id as ScanMode)}
                                        >
                                            {scanMode === mode.id && <div className="absolute left-0 top-0 bottom-0 w-1 bg-rag-blue shadow-[0_0_10px_#3b82f6]"></div>}
                                            <span className={`text-[10px] font-black uppercase tracking-widest italic ${scanMode === mode.id ? 'text-rag-blue-bright' : 'text-silver/20 group-hover:text-silver/40'}`}>{mode.label}</span>
                                            <p className="text-[11px] text-silver/40 leading-snug italic">{mode.desc}</p>
                                        </button>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* 03. Tactical Parameters (Conditional) */}
                        <section className="space-y-12">
                            <div className="flex items-baseline gap-6 border-b border-accent-silver/5 pb-4">
                                <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic">{nextNum()}. Functional_Payloads</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
                                
                                {/* Network Scanner Blocks */}
                                {isNetworkScanner && (
                                    <>
                                        <div className="space-y-6">
                                            <label className="text-[9px] font-black uppercase tracking-[0.4em] text-silver/40 italic block border-l-2 border-rag-blue pl-4">Network_Protocol</label>
                                            <div className="flex gap-1 bg-accent-silver/5 p-1 rounded-sm">
                                                {['TCP', 'UDP', 'Both'].map(p => (
                                                    <button 
                                                        key={p}
                                                        className={`flex-1 py-3 text-[9px] font-black uppercase tracking-widest italic transition-all ${networkProtocol === p ? 'bg-silver-bright text-charcoal shadow-lg scale-[1.02]' : 'text-silver/20 hover:text-silver/60'}`}
                                                        onClick={() => setNetworkProtocol(p)}
                                                    >
                                                        {p}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="space-y-6">
                                            <label className="text-[9px] font-black uppercase tracking-[0.4em] text-silver/40 italic block border-l-2 border-rag-blue pl-4">Port_Range_Optimization</label>
                                            <select className="w-full bg-charcoal border border-accent-silver/10 p-5 font-mono text-[11px] text-silver-bright focus:outline-none focus:border-silver/40 italic appearance-none" value={portSelection} onChange={(e) => setPortSelection(e.target.value)}>
                                                <option value="common">Common ports (100) — Low Noise</option>
                                                <option value="top">Top ports (1000) — Standard</option>
                                                <option value="all">All ports (65535) — Heavy Load</option>
                                                <option value="custom">Custom definition...</option>
                                            </select>
                                        </div>
                                    </>
                                )}

                                {/* Website & Vuln Detection Grid */}
                                {(isWebsiteScanner || isWebRecon || isApiScanner || isTlsScanner || isSecretScanner) && (
                                    <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-12">
                                        <div className="space-y-6">
                                            <label className="text-[9px] font-black uppercase tracking-[0.4em] text-silver/40 italic block border-l-2 border-rag-blue pl-4">Detection_Matrix_L1</label>
                                            <div className="space-y-4">
                                                {isWebsiteScanner && Object.entries(webChecks).map(([key, val]) => (
                                                    <label key={key} className="flex items-center gap-5 cursor-pointer group">
                                                        <div className="relative w-4 h-4 border border-accent-silver/10 rounded-sm flex items-center justify-center">
                                                            <input type="checkbox" className="hidden peer" checked={val} onChange={() => setWebChecks(prev => ({ ...prev, [key]: !val }))} />
                                                            <div className="w-1.5 h-1.5 bg-rag-blue opacity-0 peer-checked:opacity-100 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
                                                        </div>
                                                        <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-silver/30 group-hover:text-silver/60 italic">{key.replace(/([A-Z])/g, '_$1')}</span>
                                                    </label>
                                                ))}
                                                {isTlsScanner && Object.entries(certChecks).map(([key, val]) => (
                                                    <label key={key} className="flex items-center gap-5 cursor-pointer group">
                                                        <div className="relative w-4 h-4 border border-accent-silver/10 rounded-sm flex items-center justify-center">
                                                            <input type="checkbox" className="hidden peer" checked={val} onChange={() => setCertChecks(prev => ({ ...prev, [key]: !val }))} />
                                                            <div className="w-1.5 h-1.5 bg-rag-blue opacity-0 peer-checked:opacity-100 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
                                                        </div>
                                                        <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-silver/30 group-hover:text-silver/60 italic">CRYPT_{key.toUpperCase()}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="space-y-6">
                                            <label className="text-[9px] font-black uppercase tracking-[0.4em] text-silver/40 italic block border-l-2 border-rag-amber pl-4">Detection_Matrix_L2</label>
                                            <div className="space-y-4">
                                                {isWebsiteScanner && Object.entries(vulnDetection).map(([key, val]) => (
                                                    <label key={key} className="flex items-center gap-5 cursor-pointer group">
                                                        <div className="relative w-4 h-4 border border-accent-silver/10 rounded-sm flex items-center justify-center">
                                                            <input type="checkbox" className="hidden peer" checked={val} onChange={() => setVulnDetection(prev => ({ ...prev, [key]: !val }))} />
                                                            <div className="w-1.5 h-1.5 bg-rag-amber opacity-0 peer-checked:opacity-100 shadow-[0_0_10px_rgba(245,158,11,0.5)]"></div>
                                                        </div>
                                                        <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-silver/30 group-hover:text-silver/60 italic">VULN_{key.toUpperCase()}</span>
                                                    </label>
                                                ))}
                                                {isTlsScanner && Object.entries(protocolChecks).map(([key, val]) => (
                                                    <label key={key} className="flex items-center gap-5 cursor-pointer group">
                                                        <div className="relative w-4 h-4 border border-accent-silver/10 rounded-sm flex items-center justify-center">
                                                            <input type="checkbox" className="hidden peer" checked={val} onChange={() => setProtocolChecks(prev => ({ ...prev, [key]: !val }))} />
                                                            <div className="w-1.5 h-1.5 bg-rag-amber opacity-0 peer-checked:opacity-100 shadow-[0_0_10px_rgba(245,158,11,0.5)]"></div>
                                                        </div>
                                                        <span className="text-[10px] uppercase font-bold tracking-[0.2em] text-silver/30 group-hover:text-silver/60 italic">PROTO_{key.toUpperCase()}</span>
                                                    </label>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Specific for Fuzzer */}
                                {isFuzzer && (
                                    <>
                                        <div className="space-y-6">
                                            <label className="text-[9px] font-black uppercase tracking-[0.4em] text-silver/40 italic block border-l-2 border-rag-blue pl-4">Fuzzing_Mode</label>
                                            <div className="flex gap-1 bg-accent-silver/5 p-1 rounded-sm">
                                                {['directory', 'file', 'parameter'].map(m => (
                                                    <button 
                                                        key={m}
                                                        className={`flex-1 py-3 text-[9px] font-black uppercase tracking-widest italic transition-all ${fuzzMode === m ? 'bg-silver-bright text-charcoal shadow-lg scale-[1.02]' : 'text-silver/20 hover:text-silver/60'}`}
                                                        onClick={() => setFuzzMode(m)}
                                                    >
                                                        {m}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                        <div className="space-y-6">
                                            <label className="text-[9px] font-black uppercase tracking-[0.4em] text-silver/40 italic block border-l-2 border-rag-blue pl-4">Wordlist_Selection</label>
                                            <select className="w-full bg-charcoal border border-accent-silver/10 p-5 font-mono text-[11px] text-silver-bright focus:outline-none focus:border-silver/40 italic appearance-none" value={wordlist} onChange={(e) => setWordlist(e.target.value)}>
                                                <option value="common">common.txt (4.6k)</option>
                                                <option value="directory-list-2.3">directory-list-2.3-med.txt (220k)</option>
                                                <option value="custom">Custom_Upload...</option>
                                            </select>
                                        </div>
                                    </>
                                )}
                            </div>
                        </section>

                        {/* 04. Expert Mode Section */}
                        <section className="space-y-8 bg-black/20 p-10 border border-dashed border-accent-silver/10 rounded-sm">
                            <div className="flex justify-between items-center">
                                <div className="space-y-1">
                                    <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic">04. Terminal_Infrastructure</h3>
                                    <p className="text-[9px] text-silver/10 uppercase tracking-widest font-mono italic">High-Level_Proxy_Settings</p>
                                </div>
                                <button 
                                    className={`px-6 py-2 border text-[9px] font-black uppercase tracking-widest italic transition-all ${showExpertMode ? 'bg-rag-amber/10 border-rag-amber/40 text-rag-amber' : 'border-accent-silver/20 text-silver/40 hover:text-white'}`}
                                    onClick={() => setShowExpertMode(!showExpertMode)}
                                >
                                    {showExpertMode ? '[ DISENGAGE_EXPERT_MODE ]' : '[ ACTIVATE_EXPERT_OVERRIDE ]'}
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                                <div className="space-y-6">
                                    <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">Simulation_Engine (UA)</label>
                                    <select className="w-full bg-charcoal border border-accent-silver/5 p-4 font-mono text-[10px] text-silver/60 focus:outline-none focus:border-silver/20 italic" value={userAgent} onChange={(e) => setUserAgent(e.target.value)}>
                                        <option value="SecuScan/1.0">SecuScan_Native_1.0</option>
                                        <option value="Mozilla/5.0">Legacy_Chromium_Enclave</option>
                                    </select>
                                </div>
                                <div className="space-y-6">
                                    <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">Transmission_Timeout (s)</label>
                                    <input type="number" className="w-full bg-charcoal border border-accent-silver/5 p-4 font-mono text-[10px] text-silver/60 focus:outline-none focus:border-silver/20 italic" value={requestTimeout} onChange={(e) => setRequestTimeout(Number(e.target.value))} />
                                </div>
                            </div>

                            {showExpertMode && (
                                <div className="space-y-6 animate-in slide-in-from-top-4 duration-500">
                                    <div className="p-6 bg-rag-red/5 border border-rag-red/20 flex gap-6 items-center">
                                        <span className="material-symbols-outlined text-rag-red text-sm">warning</span>
                                        <p className="text-[10px] text-rag-red/60 font-medium italic uppercase tracking-widest">Warning: Raw CLI arguments will bypass tactical UI validation enclaves.</p>
                                    </div>
                                    <div className="space-y-4">
                                        <label className="text-[9px] font-black uppercase tracking-widest text-silver/40 italic block ml-1">Raw_Subsystem_Arguments</label>
                                        <textarea 
                                            className="w-full bg-black/40 border border-accent-silver/10 p-6 font-mono text-xs text-silver-bright focus:outline-none focus:border-rag-amber/40 transition-all italic placeholder:text-silver/5"
                                            rows={4} 
                                            placeholder="e.g. -p- -sV -A --script vuln" 
                                            value={rawFlags} 
                                            onChange={(e) => setRawFlags(e.target.value)} 
                                        />
                                    </div>
                                </div>
                            )}
                        </section>
                    </div>

                    {/* Right Column: Execution Terminal */}
                    <aside className="space-y-12">
                        
                        {/* Risk / Safety Assessment */}
                        <section className="space-y-8 bg-charcoal p-10 border border-accent-silver/10 executive-border relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-5">
                                <span className="material-symbols-outlined text-6xl">verified_user</span>
                            </div>
                            
                            <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic border-b border-accent-silver/10 pb-4">Operation_Risk</h3>
                            <div className="space-y-8">
                                <div className="flex justify-between items-baseline">
                                    <span className="text-[10px] uppercase font-bold tracking-widest text-silver/30 italic">Threat_Profile</span>
                                    <span className={`px-4 py-1 border text-[10px] font-black uppercase tracking-widest italic font-mono ${getRiskBadgeColor(tool.riskLevel)}`}>
                                        {tool.riskLevel}
                                    </span>
                                </div>
                                <div className="flex justify-between items-baseline">
                                    <span className="text-[10px] uppercase font-bold tracking-widest text-silver/30 italic">Operation_Intensity</span>
                                    <span className="text-[11px] font-mono text-silver-bright italic">
                                        {isNetworkScanner ? timingTemplate : 'STABLE_ALPHA'}
                                    </span>
                                </div>
                                <div className="space-y-4 pt-4 border-t border-accent-silver/5">
                                    <span className="text-[9px] uppercase font-black text-silver/10 tracking-[0.3em] italic">System_Saturation_Projection</span>
                                    <div className="h-1 bg-accent-silver/5 w-full relative">
                                        <div className={`absolute inset-y-0 left-0 transition-all duration-1000 shadow-[0_0_8px] ${
                                            tool.riskLevel === 'aggressive' ? 'bg-rag-red w-[85%] shadow-rag-red/40' : 
                                            tool.riskLevel === 'active' ? 'bg-rag-amber w-[45%] shadow-rag-amber/40' : 'bg-rag-blue w-[15%] shadow-rag-blue/40'
                                        }`}></div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Authorization Enclave */}
                        <section className="space-y-10">
                            <h3 className="text-xs font-black uppercase tracking-[0.4em] text-silver/20 italic border-b border-accent-silver/10 pb-4">Authorization_Token</h3>
                            {(isTlsScanner || isWebRecon || isUtils) ? (
                                <p className="text-[11px] text-silver/40 font-light leading-relaxed italic border-l-2 border-rag-blue pl-6 py-2">
                                    Informational_Recon: No explicit extraction consent required for public infrastructure metadata.
                                </p>
                            ) : (
                                <label className="flex gap-6 cursor-pointer group">
                                    <div className={`mt-1 flex-shrink-0 w-6 h-6 border transition-all flex items-center justify-center rounded-sm ${
                                        consentGranted ? 'border-rag-green bg-rag-green/10' : 'border-accent-silver/20 group-hover:border-silver/40'
                                    }`}>
                                        <input 
                                            type="checkbox" 
                                            className="hidden"
                                            checked={consentGranted} 
                                            onChange={(e) => setConsentGranted(e.target.checked)} 
                                        />
                                        {consentGranted && <span className="material-symbols-outlined text-sm text-rag-green font-black">done</span>}
                                    </div>
                                    <div className="space-y-2">
                                        <span className={`text-[11px] font-bold uppercase tracking-widest italic block transition-colors ${consentGranted ? 'text-rag-green' : 'text-silver/40 group-hover:text-silver/60'}`}>Target_Test_Consent</span>
                                        <p className="text-[9px] text-silver/20 leading-relaxed italic uppercase tracking-[0.05em]">I affirm full legal authorization to conduct security probes against this infrastructure node.</p>
                                    </div>
                                </label>
                            )}
                        </section>

                        {/* Action Primary */}
                        <div className="space-y-6 pt-12">
                            <button 
                                className={`w-full py-6 text-[11px] font-black uppercase tracking-[0.5em] italic transition-all relative group overflow-hidden ${
                                    (!isTargetValid || (!(isTlsScanner || isWebRecon || isUtils) && !consentGranted) || submitting) 
                                    ? 'bg-charcoal border border-accent-silver/10 text-silver/10 cursor-not-allowed' 
                                    : 'bg-silver-bright text-charcoal-dark hover:bg-white shadow-[0_15px_35px_rgba(0,0,0,0.5)] active:scale-95'
                                }`}
                                disabled={submitting || !isTargetValid || (!(isTlsScanner || isWebRecon || isUtils) && !consentGranted)}
                                onClick={handleStartScan}
                            >
                                <span className="relative z-10">{submitting ? 'EXECUTING_PAYLOAD...' : 'INITIATE_OPERATION'}</span>
                                {submitting && <div className="absolute inset-0 bg-white/20 animate-pulse"></div>}
                            </button>
                            <button 
                                className="w-full py-4 text-[9px] font-black uppercase tracking-[0.3em] italic text-silver/20 border border-accent-silver/5 hover:border-accent-silver/20 hover:text-silver/40 transition-all"
                                disabled
                            >
                                [ SCHEDULE_DEFERRED_SCAN ]
                            </button>
                        </div>
                        
                        <div className="pt-12 text-center opacity-10 select-none pointer-events-none">
                            <span className="text-[8px] font-black uppercase tracking-[0.8em] text-silver">COMMAND_AUTH_REQUIRED_FOR_ROOT</span>
                        </div>
                    </aside>
                </div>
            </main>
        </div>
    )
}
