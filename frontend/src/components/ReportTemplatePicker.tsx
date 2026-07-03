import React, { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getTemplates,
  getTemplateById,
  renderTemplate,
  renderPreview,
  exportAsFile,
  buildTemplateData,
  type ReportTemplate,
  type ReportTemplateType,
  type TemplateData,
} from '../services/reportTemplates'
import { CheckCircleIcon, AlertTriangleIcon } from 'lucide-react'

interface ReportTemplatePickerProps {
  reportName: string
  reportType: ReportTemplateType
  generatedAt: string
  findings: number
  assets: number
  pages: number
  summary?: {
    critical_findings?: number
    high_findings?: number
    medium_findings?: number
    low_findings?: number
    total_findings?: number
  }
  isOpen: boolean
  onClose: () => void
}

export default function ReportTemplatePicker({
  reportName,
  reportType,
  generatedAt,
  findings,
  assets,
  pages,
  summary,
  isOpen,
  onClose,
}: ReportTemplatePickerProps) {
  const [selectedId, setSelectedId] = useState<string>(() => {
    const exact = getTemplates().find(t => t.type === reportType)
    return exact?.id ?? getTemplates(reportType)[0]?.id ?? getTemplates()[0]?.id ?? ''
  })
  const [previewHtml, setPreviewHtml] = useState<string>('')
  const [showPreview, setShowPreview] = useState(false)
  const [exported, setExported] = useState(false)

  const allTemplates = useMemo(() => getTemplates(), [])
  const filteredTemplates = useMemo(() => {
    const exact = allTemplates.filter(t => t.type === reportType)
    const others = allTemplates.filter(t => t.type !== reportType)
    return [...exact, ...others]
  }, [allTemplates, reportType])

  const selectedTemplate = useMemo(() => getTemplateById(selectedId), [selectedId])

  const templateData = useMemo<TemplateData>(() => buildTemplateData(
    { name: reportName, type: reportType, generated_at: generatedAt, findings, assets, pages },
    summary,
  ), [reportName, reportType, generatedAt, findings, assets, pages, summary])

  function handleSelect(id: string) {
    setSelectedId(id)
    setShowPreview(false)
    setExported(false)
  }

  function handlePreview() {
    if (!selectedTemplate) return
    const html = renderPreview(selectedTemplate, templateData)
    setPreviewHtml(html)
    setShowPreview(true)
  }

  function handleExport() {
    if (!selectedTemplate) return
    const content = renderTemplate(selectedTemplate, templateData)
    const date = new Date().toISOString().split('T')[0]
    exportAsFile(content, `secuscan_${selectedTemplate.type}_${date}`)
    setExported(true)
    setTimeout(() => setExported(false), 2500)
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="slideover-backdrop"
        onClick={onClose}
      />
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className="slideover w-full max-w-lg"
      >
        <div className="flex items-center justify-between px-6 py-5 border-b-4 border-black bg-[#0c0c0f]">
          <div>
            <h2 className="text-base font-black text-silver-bright uppercase tracking-tight">Template Selector</h2>
            <p className="text-[9px] font-mono text-silver/40 uppercase tracking-widest mt-0.5">Multi-Format Report Engine</p>
          </div>
          <button onClick={onClose} className="text-silver/45 hover:text-silver-bright transition-colors">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        <div className="slideover-content p-6 space-y-6 custom-scrollbar overflow-y-auto flex-1">
          <div className="space-y-4">
            <h3 className="text-[9px] font-black text-silver/30 uppercase tracking-[0.25em] italic">Available Templates</h3>
            {filteredTemplates.map((tpl) => (
              <button
                key={tpl.id}
                onClick={() => handleSelect(tpl.id)}
                className={`w-full text-left p-5 border-4 transition-all ${
                  selectedId === tpl.id
                    ? 'bg-rag-blue/10 border-rag-blue shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                    : 'bg-charcoal border-black hover:border-silver/20'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 text-[8px] font-black uppercase italic border-2 border-black ${
                        tpl.type === 'executive' ? 'bg-silver-bright text-black' :
                        tpl.type === 'compliance' ? 'bg-rag-green text-black' :
                        'bg-rag-blue text-black'
                      }`}>{tpl.type}</span>
                      <span className="text-xs font-black text-silver-bright uppercase tracking-tight truncate">{tpl.name}</span>
                    </div>
                    <p className="text-[9px] font-mono text-silver/40 leading-relaxed">{tpl.description}</p>
                  </div>
                  {selectedId === tpl.id && (
                    <span className="text-rag-blue shrink-0 mt-1">
                      <CheckCircleIcon size={16} />
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>

          {showPreview && previewHtml && (
            <div className="border-4 border-black bg-charcoal overflow-hidden">
              <div className="bg-black/30 px-4 py-2 border-b-4 border-black flex items-center justify-between">
                <span className="text-[8px] font-black text-silver/30 uppercase tracking-[0.3em] italic">Live Preview</span>
                <button onClick={() => setShowPreview(false)} className="text-silver/30 hover:text-silver-bright text-[9px] font-black uppercase tracking-widest">
                  Close
                </button>
              </div>
              <div className="p-4" dangerouslySetInnerHTML={{ __html: previewHtml }} />
            </div>
          )}

          <div className="flex gap-4 pt-4 border-t-4 border-black">
            <button
              onClick={handlePreview}
              disabled={!selectedTemplate}
              className="flex-1 bg-charcoal-dark border-4 border-black px-5 py-3 text-[9px] font-black uppercase tracking-widest text-silver/70 hover:text-silver-bright hover:bg-charcoal transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Preview
            </button>
            <button
              onClick={handleExport}
              disabled={!selectedTemplate}
              className={`flex-1 border-4 border-black px-5 py-3 text-[9px] font-black uppercase tracking-widest transition-all disabled:opacity-30 disabled:cursor-not-allowed ${
                exported
                  ? 'bg-rag-green text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
                  : 'bg-rag-amber text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5'
              }`}
            >
              {exported ? 'Exported!' : 'Export .md'}
            </button>
          </div>

          {exported && (
            <div className="flex items-center gap-3 bg-rag-green/10 border-4 border-rag-green p-4">
              <AlertTriangleIcon size={14} className="text-rag-green shrink-0" />
              <p className="text-[9px] font-black text-rag-green uppercase tracking-widest">Template exported successfully</p>
            </div>
          )}

          <div className="p-5 border-4 border-black border-dashed bg-charcoal-dark/50">
            <h4 className="text-[9px] font-black text-silver/40 uppercase tracking-[0.2em] italic mb-3">Template Data Contract</h4>
            <div className="grid grid-cols-2 gap-2 text-[8px] font-mono text-silver/30">
              <span>Findings: {templateData.totalFindings}</span>
              <span>Assets: {templateData.totalAssets}</span>
              <span>Critical: {templateData.criticalCount}</span>
              <span>High: {templateData.highCount}</span>
              <span>Medium: {templateData.mediumCount}</span>
              <span>Low: {templateData.lowCount}</span>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
