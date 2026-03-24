import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
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
    const [networkScanOptions] = useState({
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
    const [websiteScope] = useState({
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

    const SectionHeader = ({ num, title }: { num: string, title: string }) => (
      <div className="flex items-center gap-6 mb-8 group">
          <div className="bg-black text-white px-3 py-1 text-xs font-black shadow-[4px_4px_0px_0px_rgba(59,130,246,0.5)]">{num}</div>
          <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic group-hover:text-rag-blue transition-colors">{title}</h3>
          <div className="h-0.5 flex-1 bg-black/10"></div>
      </div>
    )

    const Toggle = ({ checked, onChange, label, description }: any) => (
      <button 
          onClick={() => onChange(!checked)}
          className={`flex items-center justify-between p-6 bg-charcoal border-4 border-black transition-all group hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 ${
              checked ? 'shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' : 'shadow-none opacity-60'
          }`}
      >
          <div className="space-y-1 text-left">
              <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block">{label}</label>
              <span className="text-[9px] text-silver/40 uppercase tracking-tighter italic font-mono font-bold leading-none">{description}</span>
          </div>
          <div className={`w-12 h-6 border-4 border-black relative transition-all ${checked ? 'bg-rag-green' : 'bg-charcoal-dark'}`}>
              <div className={`absolute top-0 w-4 h-full bg-black transition-all ${checked ? 'left-6' : 'left-0'}`}></div>
          </div>
      </button>
    )

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            
            {/* Neo-Brutalist Deployment Header */}
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-black/20">
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <button 
                        onClick={() => navigate('/scanner')}
                        className="w-12 h-12 flex items-center justify-center border-4 border-black bg-charcoal hover:bg-rag-blue hover:text-black transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-1 active:translate-y-1"
                    >
                        <span className="material-symbols-outlined font-black">arrow_back</span>
                    </button>
                    <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest font-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                      DPL_ID: {tool.id.substring(0,8)}
                    </div>
                  </div>
                  <div className="space-y-2">
                    <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
                      {tool.name.split(' ')[0]} <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>{tool.name.split(' ').slice(1).join('_')}</span>
                    </h1>
                    <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed pt-2">
                      INITIATING_SEQUENCE // {tool.purpose}
                    </p>
                  </div>
                </div>

                <div className="hidden lg:flex flex-col items-end gap-2 text-right">
                  <span className="text-[10px] font-black text-silver/20 uppercase tracking-[0.5em] italic">RISK_PROTOCOL</span>
                  <div className={`px-6 py-2 border-4 border-black text-black font-black uppercase tracking-widest shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] ${
                    tool.risk === 'passive' ? 'bg-rag-blue' : tool.risk === 'active' ? 'bg-rag-amber' : 'bg-rag-red'
                  }`}>
                    {tool.risk}_LEVEL
                  </div>
                </div>
            </header>

            <main className="grid grid-cols-1 xl:grid-cols-4 gap-12 pt-4">
                
                {/* Configuration Columns */}
                <div className="xl:col-span-3 space-y-16">
                    
                    {/* 01. TARGET VECTORS */}
                    <section className="space-y-10">
                        <SectionHeader num="01" title="Target_Vectors" />
                        
                        <div className="bg-charcoal border-4 border-black p-10 shadow-[10px_10px_0px_0px_rgba(59,130,246,0.3)] space-y-8">
                            <div className="space-y-4">
                                <label className="text-xs font-black uppercase tracking-[0.3em] text-silver-bright italic flex items-center gap-3">
                                  <span className="material-symbols-outlined text-sm">wifi_tethering</span>
                                  Endpoint_Specification
                                </label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        className={`w-full bg-charcoal-dark border-4 border-black p-8 font-mono text-xl text-silver-bright focus:outline-none focus:ring-4 focus:ring-rag-blue/20 transition-all placeholder:text-silver/10 italic ${
                                            (isFuzzer && !targetHasPlaceholder && target.length > 0) ? 'border-rag-red text-rag-red shadow-[0_0_20px_rgba(244,63,94,0.2)]' : ''
                                        }`}
                                        placeholder={isFuzzer ? 'e.g. HTTPS://SERVER.COM/FUZZ' : (isSubdomainFinder ? 'e.g. DOMAIN.COM' : 'e.g. HTTPS://TARGET.LOCAL')}
                                        value={target}
                                        onChange={(e) => setTarget(e.target.value.toUpperCase())}
                                    />
                                    <div className="absolute right-8 top-1/2 -translate-y-1/2 flex gap-4 opacity-10 pointer-events-none">
                                        <span className="material-symbols-outlined text-2xl font-black">terminal</span>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-8 pt-4">
                                  {(isWebsiteScanner || isFuzzer || isWebRecon || isApiScanner || isXss || isSqli) && (
                                      <label className="flex items-center gap-4 cursor-pointer group">
                                          <div className="relative w-6 h-6 border-4 border-black bg-charcoal-dark flex items-center justify-center transition-all group-hover:scale-110">
                                              <input 
                                                  type="checkbox" 
                                                  className="hidden peer"
                                                  checked={followRedirects} 
                                                  onChange={(e) => setFollowRedirects(e.target.checked)} 
                                              />
                                              <div className="w-2.5 h-2.5 bg-rag-blue opacity-0 peer-checked:opacity-100 transition-opacity"></div>
                                          </div>
                                          <span className="text-[10px] uppercase font-black tracking-widest text-silver/40 group-hover:text-silver-bright italic transition-colors">AUTO_FOLLOW_30X</span>
                                      </label>
                                  )}
                                  {isTlsScanner && (
                                      <div className="flex items-center gap-4">
                                          <span className="text-[10px] font-black uppercase tracking-widest text-silver/20 italic">SYMMETRY_PORT:</span>
                                          <input type="text" className="w-24 bg-charcoal-dark border-4 border-black py-2 px-4 font-mono text-xs text-silver-bright text-center italic" value={tlsPort} onChange={(e) => setTlsPort(e.target.value)} />
                                      </div>
                                  )}
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* 02. MODE OVERRIDE */}
                    {!isWebRecon && !isUtils && !isSecretScanner && (
                        <section className="space-y-10">
                            <SectionHeader num="02" title="Protocol_Overrides" />
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                                {[
                                    { id: 'light', label: 'PASSIVE_STEALTH', color: 'bg-rag-blue', desc: 'MIN_FOOTPRINT // SAFE_TX' },
                                    { id: 'deep', label: 'ACTIVE_DEEP', color: 'bg-rag-amber', desc: 'MAX_COVERAGE // HEAVY_RX' },
                                    { id: 'custom', label: 'TACTICAL_MAN', color: 'bg-rag-red', desc: 'FULL_ARGS // MANUAL_MOD' }
                                ].map(mode => (
                                    <button 
                                        key={mode.id}
                                        className={`p-10 border-4 border-black transition-all text-left flex flex-col gap-6 relative overflow-hidden group ${
                                            scanMode === mode.id 
                                            ? 'bg-charcoal shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] -translate-x-1 -translate-y-1' 
                                            : 'bg-charcoal-dark opacity-40 hover:opacity-100'
                                        }`}
                                        onClick={() => setScanMode(mode.id as ScanMode)}
                                    >
                                        <div className={`w-12 h-1 ${mode.color}`}></div>
                                        <span className={`text-xs font-black uppercase tracking-[0.2em] italic ${scanMode === mode.id ? 'text-silver-bright' : 'text-silver/20'}`}>{mode.label}</span>
                                        <p className="text-[10px] font-black font-mono text-silver/40 leading-none italic">{mode.desc}</p>
                                        {scanMode === mode.id && <div className="absolute right-4 top-4 text-rag-blue font-black italic text-[8px]">ACTIVE</div>}
                                    </button>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* 03. FUNCTIONAL PAYLOADS */}
                    <section className="space-y-10">
                        <SectionHeader num="03" title="Operational_Payloads" />
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            {/* Conditional Rendering of Tool Specifics would go here */}
                            {/* Simplifying for space, but keeping the blocky toggle aesthetic */}
                            {isNetworkScanner && (
                                <>
                                  <div className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                                    <h4 className="text-[10px] font-black text-rag-blue uppercase tracking-widest italic border-b-2 border-black pb-2">NET_PROTOCOL_SELECTION</h4>
                                    <div className="grid grid-cols-3 gap-2">
                                        {['TCP', 'UDP', 'BOTH'].map(p => (
                                            <button 
                                                key={p}
                                                className={`py-3 text-[10px] font-black uppercase tracking-widest italic border-2 border-black transition-all ${networkProtocol === p ? 'bg-rag-blue text-black' : 'bg-charcoal-dark text-silver/20'}`}
                                                onClick={() => setNetworkProtocol(p)}
                                            >
                                                {p}
                                            </button>
                                        ))}
                                    </div>
                                  </div>
                                  <div className="grid grid-cols-1 gap-6">
                                    <Toggle label="SERVICE_DETECTION" description="BANNER_GRABBING_ACTIVE" checked={enumerationSuite.serviceVersion} onChange={(val: boolean) => setEnumerationSuite({...enumerationSuite, serviceVersion: val})} />
                                    <Toggle label="OS_FINGERPRINT" description="STACK_ANALYSIS_MOD" checked={enumerationSuite.osDetection} onChange={(val: boolean) => setEnumerationSuite({...enumerationSuite, osDetection: val})} />
                                  </div>
                                </>
                            )}

                            {isWebsiteScanner && (
                                <>
                                  <Toggle label="TLS_SECURITY_CHECKS" description="CERT_CHAIN_VALIDATION" checked={webChecks.tlsConfig} onChange={(val: boolean) => setWebChecks({...webChecks, tlsConfig: val})} />
                                  <Toggle label="CMS_RECOGNITION" description="APP_STACK_FINGERPRINT" checked={webChecks.cmsDetection} onChange={(val: boolean) => setWebChecks({...webChecks, cmsDetection: val})} />
                                  <Toggle label="SQL_INJECTION_P" description="DB_ESCAPE_ANALYSIS" checked={vulnDetection.sqli} onChange={(val: boolean) => setVulnDetection({...vulnDetection, sqli: val})} />
                                  <Toggle label="XSS_SCRIPT_P" description="DOM_SINK_ANALYSIS" checked={vulnDetection.xss} onChange={(val: boolean) => setVulnDetection({...vulnDetection, xss: val})} />
                                </>
                            )}

                            {/* Default Global Params */}
                            <div className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                                <h4 className="text-[10px] font-black text-silver-bright uppercase tracking-widest italic border-b-2 border-black pb-2">TX_GLOBAL_PARAMETERS</h4>
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-[8px] font-black uppercase text-silver/40 italic">
                                            <span>TIMEOUT_THRESHOLD</span>
                                            <span className="text-rag-blue">{requestTimeout}s</span>
                                        </div>
                                        <input type="range" min="5" max="180" value={requestTimeout} onChange={(e) => setRequestTimeout(parseInt(e.target.value))} className="w-full accent-rag-blue" />
                                    </div>
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-[8px] font-black uppercase text-silver/40 italic">
                                            <span>BURST_RATE_LIMIT</span>
                                            <span className="text-rag-amber">{requestRate}/S</span>
                                        </div>
                                        <input type="range" min="1" max="50" value={requestRate} onChange={(e) => setRequestRate(parseInt(e.target.value))} className="w-full accent-rag-amber" />
                                    </div>
                                </div>
                            </div>

                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
                                <div className="p-8 bg-charcoal-dark border-4 border-black border-dashed opacity-40 hover:opacity-100 transition-all cursor-pointer group">
                                    <span className="text-[10px] font-black text-silver-bright uppercase tracking-[0.4em] italic mb-4 block group-hover:text-rag-amber transition-colors">EXPERT_OVERRIDE</span>
                                    <p className="text-[8px] text-silver/20 font-black italic uppercase leading-none">Manual Flag Injection Protocol Area</p>
                                </div>
                                
                                {tool.requiresConsent && (
                                    <button 
                                        onClick={() => setConsentGranted(!consentGranted)}
                                        className={`p-8 border-4 border-black transition-all flex items-center justify-center gap-6 ${
                                            consentGranted ? 'bg-rag-green text-black font-black' : 'bg-rag-red/10 text-rag-red animate-pulse italic font-black'
                                        }`}
                                    >
                                        <span className="material-symbols-outlined font-black">{consentGranted ? 'check_circle' : 'warning'}</span>
                                        <span className="text-[10px] uppercase tracking-widest">LEGAL_AUTHORIZATION_{consentGranted ? 'LOGGED' : 'REQUIRED'}</span>
                                    </button>
                                )}
                            </motion.div>
                        </div>
                    </section>
                </div>

                {/* Tactical Sidebar Summary */}
                <aside className="xl:col-span-1 space-y-12">
                    <section className="bg-charcoal-dark border-4 border-black p-10 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] space-y-10 sticky top-32">
                        <div className="space-y-2">
                             <div className="w-16 h-1 w-full bg-rag-blue/20">
                                <div className="h-full bg-rag-blue w-1/3"></div>
                             </div>
                             <h3 className="text-xl font-black text-silver-bright uppercase tracking-tighter italic">TX_PREVIEW</h3>
                        </div>

                        <div className="space-y-6 pt-4 border-t-2 border-black border-dashed">
                             <div className="space-y-2">
                                <span className="text-[9px] font-black text-silver/20 uppercase tracking-widest italic">TARGET_HASH</span>
                                <p className="text-xs font-mono font-black break-all text-silver-bright">{target || 'NULL_BUFFER'}</p>
                             </div>
                             <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <span className="text-[9px] font-black text-silver/20 uppercase tracking-widest italic">PLUGIN</span>
                                    <p className="text-[10px] font-black font-mono text-rag-blue">{resolvePluginId(tool.id)?.toUpperCase() || 'UNKNOWN'}</p>
                                </div>
                                <div>
                                    <span className="text-[9px] font-black text-silver/20 uppercase tracking-widest italic">AUTH_LEVEL</span>
                                    <p className="text-[10px] font-black font-mono text-rag-amber">ROOT_SYSTEM</p>
                                </div>
                             </div>
                        </div>

                        <div className="space-y-4 pt-10">
                            <button 
                                onClick={handleStartScan}
                                disabled={!isTargetValid || (tool.requiresConsent && !consentGranted) || submitting}
                                className={`w-full py-10 border-4 border-black text-xl font-black uppercase tracking-tighter transition-all relative overflow-hidden group ${
                                    (!isTargetValid || (tool.requiresConsent && !consentGranted)) 
                                    ? 'bg-charcoal text-silver/20 cursor-not-allowed grayscale' 
                                    : 'bg-rag-blue text-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1'
                                }`}
                            >
                                <span className="relative z-10 italic">
                                    {submitting ? 'RX_INITIALIZING...' : 'EXECUTE_PROBE'}
                                </span>
                                {submitting && (
                                  <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                                )}
                            </button>
                            
                            {!isTargetValid && target.length > 0 && (
                                <p className="text-[10px] text-rag-red text-center font-black italic uppercase tracking-widest animate-bounce">
                                    {isFuzzer ? 'Missing_FUZZ_Placeholder' : 'Invalid_Target_Format'}
                                </p>
                            )}
                        </div>

                        <div className="pt-8 text-[9px] font-black text-silver/10 uppercase tracking-[0.4em] italic text-center">
                            AWAITING_OPERATOR_INPUT
                        </div>
                    </section>
                </aside>
            </main>

            {/* Subtle Background Markings */}
            <div className="fixed bottom-0 right-0 p-12 pointer-events-none opacity-[0.02] rotate-[-20deg] hidden lg:block">
                <h2 className="text-[250px] font-black italic tracking-tighter leading-none">DEPLOY</h2>
            </div>
        </div>
    )
}
