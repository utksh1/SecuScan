import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  getPluginSchema,
  listPlugins,
  getSettings,
  PluginFieldSchema,
  PluginListItem,
  PluginSchemaResponse,
  startTask,
} from '../api'
import { useToast } from '../components/ToastContext'
import { routePath, routes } from '../routes'
import { getValidationError } from '../utils/validation'

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
  const [serverLimits, setServerLimits] = useState<any | null>(null)
  const fieldRefs = useRef<Record<string, HTMLElement | null>>({})

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
        try {
          const s = await getSettings()
          setServerLimits(s || null)
        } catch (e) {
          // non-fatal; default to null
        }
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

  const validationErrors = useMemo<Record<string, string>>(() => {
    if (!schema) return {}
    return schema.fields.reduce<Record<string, string>>((errors, field) => {
      const error = getValidationError(field, inputs[field.id])
      if (error) errors[field.id] = error
      return errors
    }, {})
  }, [schema, inputs])

  const invalidFieldCount = Object.keys(validationErrors).length
  const hasValidationErrors = invalidFieldCount > 0
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
    if (hasValidationErrors) {
      const firstInvalidField = schema.fields.find((field) => validationErrors[field.id])
      if (firstInvalidField) {
        fieldRefs.current[firstInvalidField.id]?.focus()
      }
      addToast('Fix highlighted scan parameters before starting the scan.', 'error')
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
              type="button"
              aria-label="Back to scans"
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
          <p className="text-[10px] uppercase font-black tracking-[0.3em] text-rag-amber">
            Plugin unavailable
          </p>
          <p className="text-[10px] text-silver/70 uppercase tracking-widest mt-2 leading-relaxed">
            {plugin.availability.guidance ||
              `Unavailable: Requires external binaries (${plugin.availability.missing_binaries.join(', ')}). Install required tools locally to enable this scanner.`}
          </p>
          <p className="text-[9px] text-silver/40 uppercase tracking-widest mt-3">
            Task launch remains available, but execution may fail until dependencies are installed.
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
                const validationError = validationErrors[field.id]
                const isInvalid = Boolean(validationError)
                const inputBorderClass = isInvalid
                  ? 'border-rag-red focus:border-rag-red'
                  : 'border-black focus:border-rag-blue'
                const fieldId = `field-${field.id}`
                const labelId = `label-${field.id}`
                const helpId = `help-${field.id}`
                const errorId = `error-${field.id}`
                const describedBy = [field.help ? helpId : null, isInvalid ? errorId : null].filter(Boolean).join(' ') || undefined

                return (
                  <motion.div key={field.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                    <div className="flex items-center justify-between gap-6">
                      <label
                        htmlFor={fieldId}
                        id={labelId}
                        className="text-[10px] font-black uppercase tracking-[0.3em] text-silver-bright italic"
                      >
                        {field.label}
                        {field.required && <span className="text-rag-red ml-2" aria-hidden="true">*</span>}
                      </label>
                      {isInvalid && (
                        <span className="text-[9px] uppercase tracking-widest text-rag-red font-black" aria-live="polite">
                          invalid
                        </span>
                      )}
                    </div>

                    {field.type === 'text' ? (
                      <textarea
                        id={fieldId}
                        ref={(node) => {
                          fieldRefs.current[field.id] = node
                        }}
                        value={String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, event.target.value)}
                        placeholder={field.placeholder || ''}
                        aria-invalid={isInvalid}
                        aria-describedby={describedBy}
                        className={`w-full min-h-[120px] bg-charcoal-dark border-4 p-4 text-sm text-silver-bright focus:outline-none ${inputBorderClass}`}
                      />
                    ) : field.type === 'integer' ? (
                      <input
                        id={fieldId}
                        ref={(node) => {
                          fieldRefs.current[field.id] = node
                        }}
                        type="number"
                        min={Number(field.validation?.min ?? 1)}
                        max={Math.min(Number(field.validation?.max ?? Infinity), Number(serverLimits?.sandbox?.default_timeout ?? Infinity))}
                        value={value === '' ? '' : String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, coerceInteger(event.target.value))}
                        placeholder={field.placeholder || ''}
                        aria-invalid={isInvalid}
                        aria-describedby={describedBy}
                        className={`w-full bg-charcoal-dark border-4 p-4 text-sm text-silver-bright focus:outline-none ${inputBorderClass}`}
                      />
                    ) : field.type === 'boolean' ? (
                      <button
                        id={fieldId}
                        ref={(node) => {
                          fieldRefs.current[field.id] = node
                        }}
                        type="button"
                        onClick={() => handleFieldChange(field, !Boolean(value))}
                        aria-pressed={Boolean(value)}
                        aria-describedby={describedBy}
                        className={`w-full flex items-center justify-between p-4 border-4 border-black transition-all ${
                          value ? 'bg-rag-green text-black' : 'bg-charcoal-dark text-silver-bright'
                        }`}
                      >
                        <span className="text-[10px] font-black uppercase tracking-[0.2em]">{field.help || field.label}</span>
                        <span className="material-symbols-outlined">{value ? 'toggle_on' : 'toggle_off'}</span>
                      </button>
                    ) : field.type === 'select' ? (
                      <select
                        id={fieldId}
                        ref={(node) => {
                          fieldRefs.current[field.id] = node
                        }}
                        value={String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, event.target.value)}
                        aria-invalid={isInvalid}
                        aria-describedby={describedBy}
                        className={`w-full bg-charcoal-dark border-4 p-4 text-sm text-silver-bright focus:outline-none ${inputBorderClass}`}
                      >
                        <option value="">Select option</option>
                        {(field.options || []).map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : field.type === 'multiselect' ? (
                      <fieldset
                        ref={(node) => {
                          fieldRefs.current[field.id] = node
                        }}
                        aria-invalid={isInvalid}
                        aria-describedby={describedBy}
                        className="grid grid-cols-1 md:grid-cols-2 gap-3"
                      >
                        <legend className="sr-only">{field.label}</legend>
                        {(field.options || []).map((option) => {
                          const selected = Array.isArray(value) && value.includes(option.value)
                          return (
                            <button
                              key={option.value}
                              type="button"
                              aria-pressed={selected}
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
                      </fieldset>
                    ) : (
                      <input
                        id={fieldId}
                        ref={(node) => {
                          fieldRefs.current[field.id] = node
                        }}
                        type="text"
                        value={String(value ?? '')}
                        onChange={(event) => handleFieldChange(field, event.target.value)}
                        placeholder={field.placeholder || ''}
                        aria-invalid={isInvalid}
                        aria-describedby={describedBy}
                        className={`w-full bg-charcoal-dark border-4 p-4 text-sm text-silver-bright focus:outline-none ${inputBorderClass}`}
                      />
                    )}

                    {field.help && (
                      <p id={helpId} className="text-[10px] text-silver/40 uppercase tracking-widest">
                        {field.help}
                      </p>
                    )}
                    {isInvalid && (
                      <p id={errorId} role="alert" className="text-[10px] text-rag-red uppercase tracking-widest font-black">
                        {validationError}
                      </p>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </section>
        </div>

        <aside className="xl:col-span-1">
          <section className="bg-charcoal-dark border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] space-y-6">
            <h3 className="text-[11px] font-black text-silver-bright uppercase tracking-[0.4em] italic">Deploy_Control</h3>
            <p
              role={hasValidationErrors ? 'alert' : 'status'}
              aria-live="polite"
              className={`text-[10px] uppercase tracking-widest font-black ${
                hasValidationErrors ? 'text-rag-red' : 'text-rag-green'
              }`}
            >
              {hasValidationErrors
                ? `${invalidFieldCount} field${invalidFieldCount > 1 ? 's' : ''} need${invalidFieldCount === 1 ? 's' : ''} attention before scan start`
                : 'All fields valid'}
            </p>
            {plugin.requires_consent && (
              <div className="space-y-4 border-4 border-black bg-charcoal p-5">
                <p className="text-[10px] text-silver/60 uppercase tracking-widest leading-6">
                  {plugin.consent_message || 'This plugin requires explicit authorization before execution.'}
                </p>
                <label className="flex items-start gap-3 text-[10px] uppercase tracking-widest font-black text-silver-bright">
                  <input
                    type="checkbox"
                    checked={consentGranted}
                    onChange={(event) => setConsentGranted(event.target.checked)}
                    className="mt-0.5 w-4 h-4 shrink-0"
                  />
                  <span>I have explicit authorization for this target</span>
                </label>
              </div>
            )}
            <button
              type="button"
              onClick={handleStartScan}
              disabled={submitting}
              aria-disabled={submitting || hasValidationErrors}
              className={`w-full py-4 border-4 border-black text-black text-[10px] font-black uppercase tracking-[0.3em] transition-all ${
                submitting || hasValidationErrors
                  ? 'bg-rag-red/70 cursor-not-allowed opacity-60'
                  : 'bg-rag-red hover:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-1'
              } disabled:hover:shadow-none disabled:hover:translate-y-0`}
            >
              {submitting ? 'QUEUEING...' : 'INITIATE_SCAN'}
            </button>
            {hasValidationErrors && (
              <p role="status" className="text-[10px] text-rag-red uppercase tracking-widest font-black">
                {invalidFieldCount} invalid field{invalidFieldCount > 1 ? 's' : ''} highlighted
              </p>
            )}
            {!hasValidationErrors && (
              <p className="text-[10px] text-rag-green uppercase tracking-widest font-black">
                All fields valid
              </p>
            )}
          </section>
        </aside>
      </main>
    </div>
  )
}
