import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  getPluginSchema,
  listPlugins,
  PluginFieldSchema,
  PluginListItem,
  PluginSchemaResponse,
  startTask,
} from '../api'
import { useToast } from '../components/ToastContext'
import { routePath, routes } from '../routes'

type InputState = Record<string, unknown>

function defaultValueForField(field: PluginFieldSchema): unknown {
  if (field.default !== undefined) return field.default
  if (field.type === 'boolean') return false
  if (field.type === 'integer') return 0
  if (field.type === 'multiselect') return []
  if (field.type === 'select') return field.options?.[0]?.value ?? ''
  return ''
}

function buildDefaultInputs(fields: PluginFieldSchema[]): InputState {
  const defaults: InputState = {}
  for (const field of fields) defaults[field.id] = defaultValueForField(field)
  return defaults
}

function isRequiredFieldValid(field: PluginFieldSchema, value: unknown): boolean {
  if (!field.required) return true
  if (value === undefined || value === null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  return true
}

function resolvePresetInputs(
  fields: PluginFieldSchema[],
  presets: Record<string, Record<string, unknown>>,
  selectedPreset: string,
): InputState {
  const defaults = buildDefaultInputs(fields)
  if (!selectedPreset || !presets[selectedPreset]) return defaults
  return { ...defaults, ...presets[selectedPreset] }
}

function coerceInteger(raw: string): number | '' {
  if (!raw.trim()) return ''
  const parsed = Number.parseInt(raw, 10)
  return Number.isNaN(parsed) ? '' : parsed
}

function labelizeSafety(value: string) {
  return value.toUpperCase().replace(/_/g, ' ')
}

export default function ToolConfig() {
  const { toolId } = useParams<{ toolId: string }>()
  const navigate = useNavigate()
  const { addToast } = useToast()

  const [plugin, setPlugin] = useState<PluginListItem | null>(null)
  const [schema, setSchema] = useState<PluginSchemaResponse | null>(null)
  const [inputs, setInputs] = useState<InputState>({})
  const [selectedPreset, setSelectedPreset] = useState('')
  const [consentGranted, setConsentGranted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadConfig() {
      if (!toolId) {
        navigate(routes.scans)
        return
      }

      try {
        const pluginResponse = await listPlugins()
        const matchedPlugin = pluginResponse.plugins.find((item) => item.id === toolId && item.enabled)

        if (!matchedPlugin) {
          navigate(routes.scans)
          return
        }

        const pluginSchema = await getPluginSchema(matchedPlugin.id)
        if (cancelled) return

        const presetNames = Object.keys(pluginSchema.presets || {})
        const defaultPreset = presetNames[0] || ''
        const initialInputs = resolvePresetInputs(pluginSchema.fields || [], pluginSchema.presets || {}, defaultPreset)

        setPlugin(matchedPlugin)
        setSchema(pluginSchema)
        setSelectedPreset(defaultPreset)
        setInputs(initialInputs)
        setConsentGranted(!matchedPlugin.requires_consent)
      } catch (error) {
        if (!cancelled) {
          addToast('Failed to load plugin configuration.', 'error')
          navigate(routes.scans)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadConfig()
    return () => {
      cancelled = true
    }
  }, [toolId, navigate, addToast])

  const presetNames = useMemo(() => Object.keys(schema?.presets || {}), [schema])
  const requiredMissing = useMemo(() => {
    if (!schema) return []
    return schema.fields.filter((field) => !isRequiredFieldValid(field, inputs[field.id]))
  }, [schema, inputs])
  const safetyLevel = String(schema?.safety?.level || 'safe')

  const handleFieldChange = (field: PluginFieldSchema, value: unknown) => {
    setInputs((prev) => ({ ...prev, [field.id]: value }))
  }

  const handlePresetChange = (preset: string) => {
    if (!schema) return
    setSelectedPreset(preset)
    setInputs(resolvePresetInputs(schema.fields || [], schema.presets || {}, preset))
  }

  const handleStartScan = async () => {
    if (!plugin || !schema || submitting) return
    if (requiredMissing.length > 0) {
      addToast('Complete all required fields before starting the scan.', 'error')
      return
    }
    if (plugin.requires_consent && !consentGranted) {
      addToast('Consent is required for this plugin.', 'error')
      return
    }

    try {
      setSubmitting(true)
      const task = await startTask(
        plugin.id,
        inputs,
        plugin.requires_consent ? consentGranted : true,
        selectedPreset || undefined,
      )
      addToast(`Task queued: ${plugin.name}`, 'success')
      navigate(routePath.task(task.task_id))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to start scan'
      addToast(message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-12">
        <div className="space-y-4 text-center">
          <div className="w-20 h-20 border-8 border-silver-bright/10 border-t-rag-blue animate-spin mx-auto shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]" />
          <p className="text-xs font-black text-silver-bright uppercase tracking-[0.5em] italic">Loading_Config...</p>
        </div>
      </div>
    )
  }

  if (!plugin || !schema) return null

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-black/20">
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(routes.scans)}
              className="w-12 h-12 flex items-center justify-center border-4 border-black bg-charcoal hover:bg-rag-blue hover:text-black transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-1 active:translate-y-1"
            >
              <span className="material-symbols-outlined font-black">arrow_back</span>
            </button>
            <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest font-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
              DPL_ID: {plugin.id.substring(0, 8)}
            </div>
          </div>
          <div className="space-y-2">
            <h1 className="text-5xl md:text-7xl text-silver-bright uppercase tracking-tighter leading-none italic font-black">
              {plugin.name}
            </h1>
            <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic leading-relaxed pt-2">
              {schema.description}
            </p>
          </div>
        </div>

        <div className="hidden lg:flex flex-col items-end gap-2 text-right">
          <span className="text-[10px] font-black text-silver/20 uppercase tracking-[0.5em] italic">RISK_PROTOCOL</span>
          <div
            className={`px-6 py-2 border-4 border-black text-black font-black uppercase tracking-widest shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] ${
              safetyLevel === 'exploit'
                ? 'bg-rag-red'
                : safetyLevel === 'intrusive'
                  ? 'bg-rag-amber'
                  : 'bg-rag-green'
            }`}
          >
            {labelizeSafety(safetyLevel)}
          </div>
        </div>
      </header>

      {plugin.availability.missing_binaries.length > 0 && (
        <section className="bg-charcoal border-4 border-rag-amber p-6 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
          <p className="text-[10px] uppercase font-black tracking-[0.3em] text-rag-amber">Dependency warning</p>
          <p className="text-[10px] text-silver/70 uppercase tracking-widest mt-2">
            Missing local binaries: {plugin.availability.missing_binaries.join(', ')}. Task launch is still allowed but may fail at runtime.
          </p>
        </section>
      )}

      <main className="grid grid-cols-1 xl:grid-cols-4 gap-12 pt-4">
        <div className="xl:col-span-3 space-y-10">
          {presetNames.length > 0 && (
            <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
              <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic mb-6">Preset_Profile</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {presetNames.map((preset) => (
                  <button
                    key={preset}
                    onClick={() => handlePresetChange(preset)}
                    className={`py-3 text-[10px] font-black uppercase tracking-[0.25em] border-4 transition-all ${
                      selectedPreset === preset
                        ? 'bg-rag-red text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                        : 'bg-charcoal-dark border-black text-silver/30 hover:text-silver-bright'
                    }`}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </section>
          )}

          <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-8">
            <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic">Input_Vector</h3>

            <div className="space-y-6">
              {schema.fields.map((field) => {
                const value = inputs[field.id]
                const isMissing = !isRequiredFieldValid(field, value)

                return (
                  <motion.div key={field.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                    <div className="flex items-center justify-between gap-6">
                      <label className="text-[10px] font-black uppercase tracking-[0.3em] text-silver-bright italic">
                        {field.label}
                        {field.required && <span className="text-rag-red ml-2">*</span>}
                      </label>
                      {isMissing && <span className="text-[9px] uppercase tracking-widest text-rag-red font-black">required</span>}
                    </div>

                    {field.type === 'text' ? (
                      <textarea
                        value={String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, event.target.value)}
                        placeholder={field.placeholder || ''}
                        className="w-full min-h-[120px] bg-charcoal-dark border-4 border-black p-4 text-sm text-silver-bright focus:outline-none focus:border-rag-blue"
                      />
                    ) : field.type === 'integer' ? (
                      <input
                        type="number"
                        value={value === '' ? '' : String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, coerceInteger(event.target.value))}
                        placeholder={field.placeholder || ''}
                        className="w-full bg-charcoal-dark border-4 border-black p-4 text-sm text-silver-bright focus:outline-none focus:border-rag-blue"
                      />
                    ) : field.type === 'boolean' ? (
                      <button
                        onClick={() => handleFieldChange(field, !Boolean(value))}
                        className={`w-full flex items-center justify-between p-4 border-4 border-black transition-all ${
                          value ? 'bg-rag-green text-black' : 'bg-charcoal-dark text-silver-bright'
                        }`}
                      >
                        <span className="text-[10px] font-black uppercase tracking-[0.2em]">{field.help || field.label}</span>
                        <span className="material-symbols-outlined">{value ? 'toggle_on' : 'toggle_off'}</span>
                      </button>
                    ) : field.type === 'select' ? (
                      <select
                        value={String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, event.target.value)}
                        className="w-full bg-charcoal-dark border-4 border-black p-4 text-sm text-silver-bright focus:outline-none focus:border-rag-blue"
                      >
                        <option value="">Select option</option>
                        {(field.options || []).map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : field.type === 'multiselect' ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {(field.options || []).map((option) => {
                          const selected = Array.isArray(value) && value.includes(option.value)
                          return (
                            <button
                              key={option.value}
                              onClick={() => {
                                const current = Array.isArray(value) ? [...value] : []
                                const next = selected
                                  ? current.filter((item) => item !== option.value)
                                  : [...current, option.value]
                                handleFieldChange(field, next)
                              }}
                              className={`p-3 border-4 border-black text-[10px] font-black uppercase tracking-[0.15em] ${
                                selected ? 'bg-rag-blue text-black' : 'bg-charcoal-dark text-silver-bright'
                              }`}
                            >
                              {option.label}
                            </button>
                          )
                        })}
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, event.target.value)}
                        placeholder={field.placeholder || ''}
                        className="w-full bg-charcoal-dark border-4 border-black p-4 text-sm text-silver-bright focus:outline-none focus:border-rag-blue"
                      />
                    )}

                    {field.help && <p className="text-[10px] text-silver/40 uppercase tracking-widest">{field.help}</p>}
                  </motion.div>
                )
              })}
            </div>
          </section>

          {plugin.requires_consent && (
            <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
              <h3 className="text-xs font-black text-silver-bright uppercase tracking-[0.4em] italic mb-6">Consent_Gate</h3>
              <p className="text-[10px] text-silver/60 uppercase tracking-widest mb-4">
                {plugin.consent_message || 'This plugin requires explicit authorization before execution.'}
              </p>
              <label className="flex items-center gap-3 text-[10px] uppercase tracking-widest font-black">
                <input
                  type="checkbox"
                  checked={consentGranted}
                  onChange={(event) => setConsentGranted(event.target.checked)}
                  className="w-4 h-4"
                />
                I have explicit authorization for this target
              </label>
            </section>
          )}
        </div>

        <aside className="xl:col-span-1">
          <section className="bg-charcoal-dark border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
            <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.4em] italic">Deploy_Control</h3>
            <button
              onClick={handleStartScan}
              disabled={submitting}
              className="w-full py-4 bg-rag-red border-4 border-black text-black text-[10px] font-black uppercase tracking-[0.3em] hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? 'QUEUEING...' : 'INITIATE_SCAN'}
            </button>
            <p className="text-[10px] text-silver/30 uppercase tracking-widest">
              Required remaining: {requiredMissing.length}
            </p>
          </section>
        </aside>
      </main>
    </div>
  )
}
