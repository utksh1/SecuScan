import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from '../components/ThemeContext'
import { useToast } from '../components/ToastContext'
import {
  authenticateWithApiKey,
  clearStoredApiKey,
  createNotificationRule,
  deleteNotificationRule,
  getStoredApiKey,
  listNotificationHistory,
  listNotificationRules,
  logoutSession,
  updateNotificationRule,
  type NotificationChannelType,
  type NotificationHistoryRow,
  type NotificationRule,
  type NotificationSeverityThreshold,
} from '../api'
import { ConfirmModal } from '../components/ConfirmModal'

function getSystemThemeForSettings(): string {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  }
  return 'dark'
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 200, damping: 25 }
  }
}

const DEFAULT_CONFIG = {
    concurrentScans: 8,
    scanTimeout: 3600,
    scanIntensity: 'standard',
    dataRetention: 30,
    shodanKey: '',
    virustotalKey: '',
    ipWhitelist: '127.0.0.1\n10.0.0.0/8',
    autoPurgeFailed: false,
    autoRescanCritical: true,
    timezone: 'auto',
    theme: 'dark',
    notifications: {
        scanComplete: true,
        criticalFindings: true,
        systemAlerts: true
    }
}

export default function Settings() {
    const { theme, setTheme, resetToSystem, isSystemControlled } = useTheme()
    const { addToast } = useToast()

    const [apiKey, setApiKey] = useState(() => getStoredApiKey() ?? '')
    const [apiKeyVisible, setApiKeyVisible] = useState(false)
    const [notificationRules, setNotificationRules] = useState<NotificationRule[]>([])
    const [notificationRulesLoading, setNotificationRulesLoading] = useState(false)
    const [notificationRulesError, setNotificationRulesError] = useState<string | null>(null)
    const [notificationHistory, setNotificationHistory] = useState<Record<string, NotificationHistoryRow[]>>({})
    const [notificationHistoryLoading, setNotificationHistoryLoading] = useState<Record<string, boolean>>({})

    const [newRule, setNewRule] = useState<{
        name: string
        severity_threshold: NotificationSeverityThreshold
        channel_type: NotificationChannelType
        target_url_or_email: string
        is_active: boolean
    }>({
        name: '',
        severity_threshold: 'high',
        channel_type: 'webhook',
        target_url_or_email: '',
        is_active: true,
    })

    const [editRules, setEditRules] = useState<Record<string, Partial<NotificationRule>>>({})

    async function refreshNotificationRules() {
        setNotificationRulesLoading(true)
        setNotificationRulesError(null)
        try {
            const rules = await listNotificationRules()
            setNotificationRules(rules)
        } catch {
            setNotificationRulesError('Failed to load notification rules')
        } finally {
            setNotificationRulesLoading(false)
        }
    }

    async function submitNewRule() {
        const trimmedName = newRule.name.trim()
        const trimmedTarget = newRule.target_url_or_email.trim()
        if (!trimmedName) {
            addToast('Rule name is required', 'error')
            return
        }
        if (!trimmedTarget) {
            addToast('Target (webhook URL or email) is required', 'error')
            return
        }
        try {
            await createNotificationRule({
                ...newRule,
                name: trimmedName,
                target_url_or_email: trimmedTarget,
            })
            addToast('Notification rule created', 'success')
            setNewRule((prev) => ({ ...prev, name: '', target_url_or_email: '' }))
            await refreshNotificationRules()
        } catch {
            addToast('Failed to create notification rule', 'error')
        }
    }

    function startEditRule(rule: NotificationRule) {
        setEditRules((prev) => ({
            ...prev,
            [rule.id]: { ...rule },
        }))
    }

    function cancelEditRule(ruleId: string) {
        setEditRules((prev) => {
            const next = { ...prev }
            delete next[ruleId]
            return next
        })
    }

    async function saveEditRule(ruleId: string) {
        const draft = editRules[ruleId]
        if (!draft) return
        const name = String(draft.name ?? '').trim()
        const target = String(draft.target_url_or_email ?? '').trim()
        if (!name) {
            addToast('Rule name is required', 'error')
            return
        }
        if (!target) {
            addToast('Target is required', 'error')
            return
        }
        try {
            await updateNotificationRule(ruleId, {
                name,
                target_url_or_email: target,
                severity_threshold: draft.severity_threshold as NotificationSeverityThreshold,
                channel_type: draft.channel_type as NotificationChannelType,
                is_active: Boolean(draft.is_active),
            })
            addToast('Notification rule updated', 'success')
            cancelEditRule(ruleId)
            await refreshNotificationRules()
        } catch {
            addToast('Failed to update notification rule', 'error')
        }
    }

    async function toggleRuleActive(rule: NotificationRule) {
        try {
            await updateNotificationRule(rule.id, { is_active: !rule.is_active })
            setNotificationRules((prev) =>
                prev.map((r) => (r.id === rule.id ? { ...r, is_active: !r.is_active } : r)),
            )
        } catch {
            addToast('Failed to update rule', 'error')
        }
    }

    async function removeRule(ruleId: string) {
        setModalState({
            isOpen: true,
            title: 'Delete rule',
            message: 'Delete this notification rule? This cannot be undone.',
            type: 'danger',
            onConfirm: async () => {
                try {
                    await deleteNotificationRule(ruleId)
                    addToast('Notification rule deleted', 'info')
                    await refreshNotificationRules()
                } catch {
                    addToast('Failed to delete notification rule', 'error')
                } finally {
                    setModalState(prev => ({ ...prev, isOpen: false }))
                }
            },
        })
    }

    async function loadRuleHistory(ruleId: string) {
        setNotificationHistoryLoading((prev) => ({ ...prev, [ruleId]: true }))
        try {
            const data = await listNotificationHistory({ rule_id: ruleId, limit: 10, offset: 0 })
            setNotificationHistory((prev) => ({ ...prev, [ruleId]: data.history }))
        } catch {
            addToast('Failed to load notification history', 'error')
        } finally {
            setNotificationHistoryLoading((prev) => ({ ...prev, [ruleId]: false }))
        }
    }

    const handleSaveApiKey = async () => {
        const trimmed = apiKey.trim()
        if (!trimmed) {
            addToast("API key cannot be empty", "error")
            return
        }
        try {
            await authenticateWithApiKey(trimmed)
            addToast("API key saved — all future requests will use this key", "success")
        } catch (err: any) {
            addToast(err?.message || "Authentication failed", "error")
        }
    }

    const handleClearApiKey = async () => {
        if (window.confirm("Clear the stored API key? The UI will return 401 errors until a valid key is configured.")) {
            setApiKey('')
            clearStoredApiKey()
            await logoutSession()
            addToast("API key cleared", "info")
        }
    }

    const [config, setConfig] = useState(() => {
        const saved = localStorage.getItem('secuscan-config')
        if (saved) {
            try {
                return { ...DEFAULT_CONFIG, ...JSON.parse(saved) }
            } catch (e) {
                return DEFAULT_CONFIG
            }
        }
        return DEFAULT_CONFIG
    })

    const [lastSavedConfig, setLastSavedConfig] = useState(config)
    const isDirty = JSON.stringify(config) !== JSON.stringify(lastSavedConfig)

    const [systemTimezone, setSystemTimezone] = useState('Detecting...')

    // Modal state for confirm dialogs
    const [modalState, setModalState] = useState<{
        isOpen: boolean;
        title: string;
        message: string;
        onConfirm: () => void;
        type: "danger" | "warning" | "info";
    }>({
        isOpen: false,
        title: "",
        message: "",
        onConfirm: () => {},
        type: "warning",
    })

    useEffect(() => {
        try {
            setSystemTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone)
        } catch (e) {
            setSystemTimezone('UTC')
        }
    }, [])

    useEffect(() => {
        refreshNotificationRules()
    }, [])

    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (!isDirty) return
            e.preventDefault()
            e.returnValue = ''
        }
        window.addEventListener('beforeunload', handleBeforeUnload)
        return () => window.removeEventListener('beforeunload', handleBeforeUnload)
    }, [isDirty])

    const handleSave = () => {
        localStorage.setItem('secuscan-config', JSON.stringify(config))
        setLastSavedConfig(config)
        addToast("Operational parameters synchronized", "success")
        setTheme(config.theme as 'dark' | 'light')
    }

    const handleReset = () => {
        setModalState({
            isOpen: true,
            title: "Engine Reset",
            message: "Restore engine to factory specifications? All API keys and custom rules will be cleared.",
            type: "warning",
            onConfirm: () => {
                setConfig(DEFAULT_CONFIG)
                setLastSavedConfig(DEFAULT_CONFIG)
                localStorage.setItem('secuscan-config', JSON.stringify(DEFAULT_CONFIG))
                addToast("Engine parameters reset to factory defaults", "info")
                setModalState(prev => ({ ...prev, isOpen: false }))
            }
        })
    }

    const handleNuclearPurge = () => {
        setModalState({
            isOpen: true,
            title: "NUCLEAR PURGE",
            message: "CRITICAL: THIS WILL PURGE ALL HISTORY AND ASSETS. PROCEED?",
            type: "danger",
            onConfirm: () => {
                Object.keys(localStorage)
                    .filter(key => key.startsWith('secuscan') || key === 'sidebar-expanded')
                    .forEach(key => localStorage.removeItem(key))
                window.location.reload()
                setModalState(prev => ({ ...prev, isOpen: false }))
            }
        })
    }

    const handleExport = () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(config, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href",     dataStr);
        downloadAnchorNode.setAttribute("download", `secuscan_config_${new Date().toISOString().split('T')[0]}.json`);
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
        addToast("Encryption export successful", "success")
    }

    const InputField = ({ label, description, type = "text", value, onChange, placeholder }: any) => (
        <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all group">
            <div className="space-y-2 mb-6">
                <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] block italic group-hover:text-rag-blue transition-colors">{label}</label>
                <p className="text-[9px] text-silver/40 uppercase font-mono font-bold tracking-widest leading-relaxed">{description}</p>
            </div>
            <input
                type={type}
                value={value}
                onChange={(e) => onChange(type === 'number' ? parseInt(e.target.value) || 0 : e.target.value)}
                placeholder={placeholder}
                className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase"
            />
        </div>
    )

    const SelectField = ({ label, description, value, onChange, options }: any) => (
        <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all group">
            <div className="space-y-2 mb-6">
                <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] block italic group-hover:text-rag-blue transition-colors">{label}</label>
                <p className="text-[9px] text-silver/40 uppercase font-mono font-bold tracking-widest leading-relaxed">{description}</p>
            </div>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase appearance-none"
            >
                {options.map((opt: any) => (
                    <option key={opt.value} value={opt.value} className="bg-charcoal text-silver-bright">{opt.label}</option>
                ))}
            </select>
        </div>
    )

    const Toggle = ({ checked, onChange, label, description, ariaLabel }: any) => (
        <button
            type="button"
            onClick={() => onChange(!checked)}
            aria-label={ariaLabel ?? label}
            className={`flex items-center justify-between p-8 bg-charcoal border-4 border-black transition-all group hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 ${
                checked ? 'shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]' : 'shadow-none'
            }`}
        >
            <div className="space-y-2 text-left mr-8">
                <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block group-hover:text-rag-green transition-colors">{label}</label>
                <span className="text-[9px] text-silver/30 uppercase tracking-tighter italic font-mono font-bold leading-relaxed">{description}</span>
            </div>
            <div className={`w-14 h-7 border-4 border-black relative shrink-0 transition-all ${checked ? 'bg-rag-green' : 'bg-charcoal-dark'}`}>
                <div className={`absolute top-0 w-5 h-full bg-black transition-all ${checked ? 'left-7' : 'left-0'}`}></div>
            </div>
        </button>
    )

    return (
        <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
            <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10 font-black">
                <div className="space-y-4">
                  <div className="bg-rag-blue text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] font-black">
                    Engine_Nexus_v4.5.3
                  </div>
                  <h1 className="text-6xl md:text-8xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
                    Core <span className="text-transparent stroke-white" style={{ WebkitTextStroke: '2px var(--accent-silver-bright)' }}>Array</span>
                  </h1>
                  <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed">
                    HARDWARE_TUNING // AUDIT_STRATEGY // SECTOR_ISOLATION
                  </p>
                </div>
                <div className="flex flex-col items-end gap-4">
                   <div className="bg-charcoal border-4 border-black px-8 py-4 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
                        <span className="text-[10px] font-black text-silver/20 uppercase tracking-[0.4em] block mb-1 italic">SYSTEM_TIMEZONE_SYNC</span>
                        <span className="text-xs font-black font-mono text-rag-blue tracking-widest italic">{systemTimezone.toUpperCase()}</span>
                    </div>
                </div>
            </header>
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-12 pt-4">
                <main className="xl:col-span-3 space-y-20">

                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">API_Key_Configuration</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Backend_API_Key</label>
                                <p className="text-[10px] text-silver/40 uppercase font-bold italic mb-4 leading-relaxed">
                                    Read from <span className="text-rag-blue font-mono">backend/data/.api_key</span> after starting the backend. Sent to the backend which sets an HttpOnly session cookie — never persisted in browser storage.
                                </p>
                            </div>
                            <div className="flex gap-4 items-stretch">
                                <input
                                    type={apiKeyVisible ? 'text' : 'password'}
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    placeholder="PASTE_KEY_HERE"
                                    className="flex-1 bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase"
                                    autoComplete="off"
                                    spellCheck={false}
                                />
                                <button
                                    onClick={() => setApiKeyVisible(v => !v)}
                                    className="px-4 bg-charcoal-dark border-4 border-black text-[10px] font-black text-silver/40 uppercase tracking-widest hover:text-white transition-colors"
                                    title={apiKeyVisible ? 'Hide key' : 'Show key'}
                                >
                                    {apiKeyVisible ? 'HIDE' : 'SHOW'}
                                </button>
                            </div>
                            <div className="flex gap-4 pt-2">
                                <button
                                    onClick={handleSaveApiKey}
                                    className="bg-rag-blue text-black px-8 py-3 text-[10px] font-black uppercase tracking-[0.3em] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all italic"
                                >
                                    SAVE_KEY
                                </button>
                                <button
                                    onClick={handleClearApiKey}
                                    className="bg-rag-red text-black px-8 py-3 text-[10px] font-black uppercase tracking-[0.3em] shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all italic"
                                >
                                    CLEAR_KEY
                                </button>
                            </div>
                            {getStoredApiKey() ? (
                                <p className="text-[10px] font-mono text-rag-green uppercase tracking-widest">
                                    ● KEY_CONFIGURED — requests will authenticate automatically
                                </p>
                            ) : (
                                <p className="text-[10px] font-mono text-rag-red uppercase tracking-widest">
                                    ● NO_KEY_SET — API requests will return 401 until a key is saved
                                </p>
                            )}
                        </div>
                    </section>

                    <section className="space-y-8" aria-label="Notification rules">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Notification_Rules</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                            <button
                                type="button"
                                onClick={refreshNotificationRules}
                                className="px-4 py-2 bg-charcoal border-4 border-black text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright hover:bg-black/40 transition-all"
                                aria-label="Refresh notification rules"
                            >
                                Refresh
                            </button>
                        </div>

                        <div className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Create_Rule</label>
                                <p className="text-[10px] text-silver/40 uppercase font-bold italic mb-4 leading-relaxed">
                                    Configure alerts for high-risk findings via webhook or email placeholder.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                <div className="bg-charcoal-dark border-4 border-black p-6 space-y-4">
                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Rule_Name</label>
                                    <input
                                        value={newRule.name}
                                        onChange={(e) => setNewRule((p) => ({ ...p, name: e.target.value }))}
                                        className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-silver-bright font-bold focus:outline-none focus:border-rag-blue/50 transition-colors"
                                        placeholder="High risk webhook"
                                        aria-label="New rule name"
                                    />
                                </div>
                                <div className="bg-charcoal-dark border-4 border-black p-6 space-y-4">
                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Target</label>
                                    <input
                                        value={newRule.target_url_or_email}
                                        onChange={(e) => setNewRule((p) => ({ ...p, target_url_or_email: e.target.value }))}
                                        className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-silver-bright font-bold focus:outline-none focus:border-rag-blue/50 transition-colors"
                                        placeholder={newRule.channel_type === 'webhook' ? 'https://example.com/hook' : 'alerts@example.com'}
                                        aria-label="New rule target"
                                    />
                                </div>
                                <div className="bg-charcoal-dark border-4 border-black p-6 space-y-4">
                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Severity_Threshold</label>
                                    <select
                                        value={newRule.severity_threshold}
                                        onChange={(e) => setNewRule((p) => ({ ...p, severity_threshold: e.target.value as NotificationSeverityThreshold }))}
                                        className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase appearance-none"
                                        aria-label="New rule severity threshold"
                                    >
                                        {(['critical','high','medium','low','info'] as NotificationSeverityThreshold[]).map((s) => (
                                            <option key={s} value={s} className="bg-charcoal text-silver-bright">{s}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="bg-charcoal-dark border-4 border-black p-6 space-y-4">
                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Channel</label>
                                    <select
                                        value={newRule.channel_type}
                                        onChange={(e) => setNewRule((p) => ({ ...p, channel_type: e.target.value as NotificationChannelType }))}
                                        className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-rag-blue font-bold focus:outline-none focus:border-rag-blue/50 transition-colors uppercase appearance-none"
                                        aria-label="New rule channel type"
                                    >
                                        {(['webhook','email'] as NotificationChannelType[]).map((c) => (
                                            <option key={c} value={c} className="bg-charcoal text-silver-bright">{c}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                                <Toggle
                                    checked={newRule.is_active}
                                    onChange={(val: boolean) => setNewRule((p) => ({ ...p, is_active: val }))}
                                    label="Active"
                                    description="RULE_ENABLED"
                                />
                                <button
                                    type="button"
                                    onClick={submitNewRule}
                                    className="bg-rag-blue text-black px-10 py-4 text-[10px] font-black uppercase tracking-[0.35em] shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all italic"
                                >
                                    CREATE_RULE
                                </button>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {notificationRulesLoading && (
                                <p className="text-[10px] font-black uppercase tracking-widest text-silver/30">Loading rules...</p>
                            )}
                            {notificationRulesError && (
                                <div className="border-4 border-rag-red bg-rag-red/10 p-6 text-rag-red text-[10px] font-black uppercase tracking-widest">
                                    {notificationRulesError}
                                </div>
                            )}
                            {!notificationRulesLoading && !notificationRulesError && notificationRules.length === 0 && (
                                <p className="text-[10px] font-black uppercase tracking-widest text-silver/30 italic">No rules yet.</p>
                            )}

                            {notificationRules.map((rule) => {
                                const draft = editRules[rule.id]
                                const isEditing = Boolean(draft)
                                const row = (draft ?? rule) as NotificationRule
                                const history = notificationHistory[rule.id] ?? []
                                const histLoading = Boolean(notificationHistoryLoading[rule.id])
                                return (
                                    <div key={rule.id} className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] space-y-6">
                                        <div className="flex flex-col lg:flex-row gap-6 lg:items-start lg:justify-between">
                                            <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4">
                                                <div className="space-y-2">
                                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Name</label>
                                                    <input
                                                        value={row.name}
                                                        disabled={!isEditing}
                                                        onChange={(e) => setEditRules((p) => ({ ...p, [rule.id]: { ...(p[rule.id] ?? {}), name: e.target.value } }))}
                                                        className={`w-full border-4 border-black p-3 text-xs font-mono font-bold focus:outline-none transition-colors ${
                                                            isEditing ? 'bg-black/40 text-silver-bright focus:border-rag-blue/50' : 'bg-black/20 text-silver/60'
                                                        }`}
                                                        aria-label={`Rule name ${rule.id}`}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Target</label>
                                                    <input
                                                        value={row.target_url_or_email}
                                                        disabled={!isEditing}
                                                        onChange={(e) => setEditRules((p) => ({ ...p, [rule.id]: { ...(p[rule.id] ?? {}), target_url_or_email: e.target.value } }))}
                                                        className={`w-full border-4 border-black p-3 text-xs font-mono font-bold focus:outline-none transition-colors ${
                                                            isEditing ? 'bg-black/40 text-silver-bright focus:border-rag-blue/50' : 'bg-black/20 text-silver/60'
                                                        }`}
                                                        aria-label={`Rule target ${rule.id}`}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Severity</label>
                                                    <select
                                                        value={row.severity_threshold}
                                                        disabled={!isEditing}
                                                        onChange={(e) => setEditRules((p) => ({ ...p, [rule.id]: { ...(p[rule.id] ?? {}), severity_threshold: e.target.value } }))}
                                                        className={`w-full border-4 border-black p-3 text-xs font-mono font-bold focus:outline-none transition-colors uppercase appearance-none ${
                                                            isEditing ? 'bg-black/40 text-rag-blue focus:border-rag-blue/50' : 'bg-black/20 text-silver/60'
                                                        }`}
                                                        aria-label={`Rule severity ${rule.id}`}
                                                    >
                                                        {(['critical','high','medium','low','info'] as NotificationSeverityThreshold[]).map((s) => (
                                                            <option key={s} value={s} className="bg-charcoal text-silver-bright">{s}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="text-[10px] font-black text-silver/50 uppercase tracking-widest">Channel</label>
                                                    <select
                                                        value={row.channel_type}
                                                        disabled={!isEditing}
                                                        onChange={(e) => setEditRules((p) => ({ ...p, [rule.id]: { ...(p[rule.id] ?? {}), channel_type: e.target.value } }))}
                                                        className={`w-full border-4 border-black p-3 text-xs font-mono font-bold focus:outline-none transition-colors uppercase appearance-none ${
                                                            isEditing ? 'bg-black/40 text-rag-blue focus:border-rag-blue/50' : 'bg-black/20 text-silver/60'
                                                        }`}
                                                        aria-label={`Rule channel ${rule.id}`}
                                                    >
                                                        {(['webhook','email'] as NotificationChannelType[]).map((c) => (
                                                            <option key={c} value={c} className="bg-charcoal text-silver-bright">{c}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            </div>

                                            <div className="space-y-3 shrink-0">
                                                <Toggle
                                                    checked={rule.is_active}
                                                    onChange={() => toggleRuleActive(rule)}
                                                    label={rule.is_active ? 'Active' : 'Inactive'}
                                                    description="TOGGLE_RULE"
                                                    ariaLabel={`Toggle rule ${rule.id}`}
                                                />
                                            </div>
                                        </div>

                                        <div className="flex flex-wrap items-center gap-3">
                                            {!isEditing ? (
                                                <>
                                                    <button
                                                        type="button"
                                                        onClick={() => startEditRule(rule)}
                                                        className="px-6 py-3 bg-charcoal-dark border-4 border-black text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright hover:bg-black/40 transition-all"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => removeRule(rule.id)}
                                                        className="px-6 py-3 bg-rag-red border-4 border-black text-[10px] font-black uppercase tracking-widest text-black hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all"
                                                    >
                                                        Delete
                                                    </button>
                                                </>
                                            ) : (
                                                <>
                                                    <button
                                                        type="button"
                                                        onClick={() => saveEditRule(rule.id)}
                                                        className="px-6 py-3 bg-rag-blue border-4 border-black text-[10px] font-black uppercase tracking-widest text-black hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all"
                                                    >
                                                        Save
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => cancelEditRule(rule.id)}
                                                        className="px-6 py-3 bg-charcoal-dark border-4 border-black text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright hover:bg-black/40 transition-all"
                                                    >
                                                        Cancel
                                                    </button>
                                                </>
                                            )}

                                            <button
                                                type="button"
                                                onClick={() => loadRuleHistory(rule.id)}
                                                className="px-6 py-3 bg-charcoal-dark border-4 border-black text-[10px] font-black uppercase tracking-widest text-silver/60 hover:text-silver-bright hover:bg-black/40 transition-all"
                                                aria-label={`Load history ${rule.id}`}
                                            >
                                                {histLoading ? 'Loading history…' : 'Load history'}
                                            </button>
                                        </div>

                                        {history.length > 0 && (
                                            <div className="border-t-4 border-black/20 pt-6 space-y-3">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-silver/40">Recent history</p>
                                                <div className="space-y-2">
                                                    {history.map((h) => (
                                                        <div key={h.id} className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 bg-black/20 border-2 border-black p-3">
                                                            <div className="text-[10px] font-mono text-silver/60">
                                                                <span className="text-silver-bright">{h.status}</span> · finding {h.finding_id}
                                                            </div>
                                                            <div className="text-[10px] font-mono text-silver/40">
                                                                {h.error_message ? `error: ${h.error_message}` : ''} {h.sent_at ? `· ${h.sent_at}` : ''}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </section>

                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Engine_Parameters</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <SelectField
                                label="Scanner_Intensity"
                                description="PACKET_DENSITY_PER_SECOND_THRESHOLD"
                                value={config.scanIntensity}
                                onChange={(val: string) => setConfig({...config, scanIntensity: val})}
                                options={[
                                    { label: 'Low (Stealth/Passive)', value: 'low' },
                                    { label: 'Standard (Balanced)', value: 'standard' },
                                    { label: 'Aggressive (Intrusive)', value: 'aggressive' },
                                ]}
                            />
                            <SelectField
                                label="Retention_Cycle"
                                description="AUTOMATED_LOG_PURGE_STRATEGY"
                                value={config.dataRetention}
                                onChange={(val: number) => setConfig({...config, dataRetention: val})}
                                options={[
                                    { label: '7 Days', value: 7 },
                                    { label: '30 Days', value: 30 },
                                    { label: '90 Days', value: 90 },
                                    { label: 'Indefinite', value: 0 },
                                ]}
                            />
                            <InputField
                                label="Concurrent_Operations"
                                description="MAX_PARALLEL_TASK_EXECUTION"
                                type="number"
                                value={config.concurrentScans}
                                onChange={(val: number) => setConfig({...config, concurrentScans: val})}
                            />
                            <InputField
                                label="Execution_Timeout"
                                description="THRESHOLD_IN_SECONDS_PER_NODE"
                                type="number"
                                value={config.scanTimeout}
                                onChange={(val: number) => setConfig({...config, scanTimeout: val})}
                            />
                        </div>
                    </section>
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Security_Interface</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <SelectField
                                label="Temporal_Logic"
                                description="UI_CHRONOS_ALIGNMENT"
                                value={config.timezone}
                                onChange={(val: string) => setConfig({...config, timezone: val})}
                                options={[
                                    { label: `Follow System (${systemTimezone})`, value: 'auto' },
                                    { label: 'UTC (Universal Coordinated)', value: 'UTC' },
                                    { label: 'Fixed (ZULU)', value: 'GMT' },
                                ]}
                            />
                            <div className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] transition-all group">
                                <div className="space-y-2 mb-6">
                                    <label className="text-[10px] font-black text-silver-bright uppercase tracking-[0.2em] block italic group-hover:text-rag-blue transition-colors">Visual_Spectrum</label>
                                    <p className="text-[9px] text-silver/40 uppercase font-mono font-bold tracking-widest leading-relaxed">OPERATIONAL_AESTHETIC_MODE</p>
                                </div>
                                <div className="space-y-3">
                                    <select
                                        value={config.theme}
                                        onChange={(e) => setConfig({ ...config, theme: e.target.value })}
                                        aria-label="Visual spectrum theme"
                                        className="w-full bg-black/40 border-4 border-black p-4 text-xs font-mono text-silver-bright focus:outline-none focus:ring-2 focus:ring-rag-blue"
                                    >
                                        <option value="dark" className="bg-charcoal text-silver-bright">Dark (Obsidian)</option>
                                        <option value="light" className="bg-charcoal text-silver-bright">Light (Paper)</option>
                                    </select>
                                    {isSystemControlled && (
                                        <p className="text-[9px] text-rag-blue/70 italic">↳ Following system preference: {getSystemThemeForSettings()}</p>
                                    )}
                                    <button
                                        onClick={resetToSystem}
                                        disabled={isSystemControlled}
                                        className="w-full py-2 text-[9px] font-bold text-silver-bright uppercase tracking-widest bg-black/30 hover:bg-black/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all border border-silver/20"
                                    >
                                        Reset to System Default
                                    </button>
                                </div>
                            </div>
                        </div>
                    </section>
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Intelligence_API_Link</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <InputField
                                label="Shodan_Enclave"
                                description="RECON_TELEMETRY_STREAM_TOKEN"
                                placeholder="SHODAN_SECRET"
                                type="password"
                                value={config.shodanKey}
                                onChange={(val: string) => setConfig({...config, shodanKey: val})}
                            />
                            <InputField
                                label="VirusTotal_Enclave"
                                description="MALWARE_INTEL_ACCESS_HASH"
                                placeholder="VT_SECRET_HASH"
                                type="password"
                                value={config.virustotalKey}
                                onChange={(val: string) => setConfig({...config, virustotalKey: val})}
                            />
                        </div>
                    </section>
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Access_Perimeters</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-silver-bright uppercase tracking-widest block italic">Authorized_Ingress_Vectors</label>
                                <p className="text-[10px] text-silver/40 uppercase font-bold italic mb-6 leading-relaxed">Line-delimited IP/CIDR whitelist for high-privilege access</p>
                            </div>
                            <textarea
                                value={config.ipWhitelist}
                                onChange={(e) => setConfig({...config, ipWhitelist: e.target.value})}
                                rows={4}
                                className="w-full bg-black/40 border-4 border-black p-6 text-xs font-mono text-rag-amber font-bold focus:outline-none focus:border-rag-amber/50 transition-colors uppercase resize-none"
                            />
                        </div>
                    </section>
                    <section className="space-y-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Audit_Logic_Toggles</h3>
                            <div className="h-0.5 flex-1 bg-black/10"></div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <Toggle
                                label="System_Signals"
                                description="CRITICAL_RX_TELEMETRY"
                                checked={config.notifications.systemAlerts}
                                onChange={(val: boolean) => setConfig({...config, notifications: {...config.notifications, systemAlerts: val}})}
                            />
                            <Toggle
                                label="Auto_Rescan"
                                description="TRIGGER_NEW_SCAN_ON_CRITICAL"
                                checked={config.autoRescanCritical}
                                onChange={(val: boolean) => setConfig({...config, autoRescanCritical: val})}
                            />
                             <Toggle
                                label="Garbage_Collection"
                                description="AUTO_PURGE_FAILED_SESSIONS"
                                checked={config.autoPurgeFailed}
                                onChange={(val: boolean) => setConfig({...config, autoPurgeFailed: val})}
                            />
                        </div>
                    </section>
                    <section className="pt-12 space-y-3">
                        {isDirty && (
                            <p role="status" className="text-[10px] font-black text-rag-amber uppercase tracking-[0.3em] italic">
                                ● UNSAVED_CHANGES_PENDING
                            </p>
                        )}
                        <button
                            onClick={handleSave}
                            className="bg-rag-blue text-black px-12 py-6 text-xs font-black uppercase tracking-[0.3em] shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-4 italic group"
                        >
                            COMMIT_ENGINE_CHANGES
                            <span className="material-symbols-outlined font-black group-hover:rotate-12 transition-transform">sync</span>
                        </button>
                    </section>
                </main>
                <aside className="xl:col-span-1 space-y-12">
                    <section className="bg-charcoal border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                        <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.5em] italic mb-8">Management_Tools</h3>
                        <div className="space-y-4">
                            <button
                                onClick={handleExport}
                                className="w-full py-4 bg-charcoal-dark border-4 border-black text-[10px] font-black text-silver/40 uppercase tracking-[0.08em] whitespace-nowrap overflow-hidden hover:bg-black hover:text-white transition-all italic"
                            >
                                TELEMETRY_EXPORT
                            </button>
                            <button
                                onClick={handleReset}
                                className="w-full py-4 bg-rag-amber border-4 border-black text-[10px] font-black text-black uppercase tracking-[0.08em] whitespace-nowrap overflow-hidden hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all italic"
                            >
                                ENGINE_RESET
                            </button>
                            <button
                                onClick={handleNuclearPurge}
                                className="w-full py-4 bg-rag-red border-4 border-black text-[10px] font-black text-black uppercase tracking-[0.08em] whitespace-nowrap overflow-hidden hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 transition-all italic"                            >
                                NUCLEAR_PURGE
                            </button>
                        </div>
                    </section>
                    <section className="bg-charcoal-dark border-4 border-black p-10 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
                        <div className="space-y-4">
                            <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.5em] italic border-b-4 border-black pb-4">Engine_Status</h3>
                            <div className="space-y-4 font-mono">
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-silver/30 uppercase tracking-tighter">Engine Version</span>
                                    <span className="text-rag-blue font-bold">4.5.3-BETA</span>
                                </div>
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-silver/30 uppercase tracking-tighter">Stack Health</span>
                                    <span className="text-rag-green font-bold">NOMINAL</span>
                                </div>
                                <div className="flex justify-between text-[10px]">
                                    <span className="text-silver/30 uppercase tracking-tighter">Core Sync</span>
                                    <span className="text-silver-bright font-bold">STABLE</span>
                                </div>
                            </div>
                        </div>
                    </section>
                </aside>
            </div>
            <footer className="pt-24 border-t-4 border-black/5 flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic opacity-20">
                <div className="flex items-center gap-6">
                    <div className="w-12 h-1 bg-silver/20"></div>
                    RESTRICTED_ACCESS_ENCLAVE // SECUSCAN_CORE_REV_4 // CLASSIFIED_VIEW
                </div>
                <div className="flex gap-4">
                    {[1,2,3,4,5,6,7,8].map(i => <div key={i} className="w-2 h-2 bg-silver/20 rounded-full"></div>)}
                </div>
            </footer>
            <ConfirmModal
                isOpen={modalState.isOpen}
                title={modalState.title}
                message={modalState.message}
                onConfirm={modalState.onConfirm}
                onCancel={() => setModalState(prev => ({ ...prev, isOpen: false }))}
                type={modalState.type}
            />
        </div>
    )
}