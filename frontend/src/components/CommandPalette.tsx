import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { routes, routePath } from '../routes'
import { useTheme } from './ThemeContext'

interface Command {
  id: string
  label: string
  description: string
  category: string
  icon: string
  shortcut?: string
  action: () => void
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const { theme, setTheme } = useTheme()

  const commands: Command[] = useMemo(() => [
    { id: 'nav-dashboard', label: 'Dashboard', description: 'Go to the main dashboard', category: 'Navigation', icon: 'dashboard', action: () => navigate(routes.dashboard) },
    { id: 'nav-toolkit', label: 'Toolkit', description: 'Browse scanner tools and templates', category: 'Navigation', icon: 'construction', action: () => navigate(routes.toolkit) },
    { id: 'nav-scans', label: 'Scans', description: 'View all scan tasks', category: 'Navigation', icon: 'radar', action: () => navigate(routes.scans) },
    { id: 'nav-findings', label: 'Findings', description: 'Browse security findings', category: 'Navigation', icon: 'bug_report', action: () => navigate(routes.findings) },
    { id: 'nav-reports', label: 'Reports', description: 'Generate and view reports', category: 'Navigation', icon: 'description', action: () => navigate(routes.reports) },
    { id: 'nav-workflows', label: 'Workflows', description: 'Manage scan workflows', category: 'Navigation', icon: 'account_tree', action: () => navigate(routes.workflows) },
    { id: 'nav-settings', label: 'Settings', description: 'Configure engine parameters', category: 'Navigation', icon: 'settings', action: () => navigate(routes.settings) },
    { id: 'action-toggle-sidebar', label: 'Toggle Sidebar', description: 'Show or hide the sidebar', category: 'Actions', icon: 'menu_open', shortcut: 'g + b', action: () => window.dispatchEvent(new CustomEvent('toggle-sidebar')) },
    { id: 'action-toggle-theme', label: 'Toggle Theme', description: 'Switch between dark and light mode', category: 'Actions', icon: 'dark_mode', action: () => setTheme(theme === 'dark' ? 'light' : 'dark') },
    { id: 'nav-nmap', label: 'Scan: Nmap', description: 'Comprehensive network discovery and port scanning', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('nmap')) },
    { id: 'nav-nikto', label: 'Scan: Nikto', description: 'Web server vulnerability scanning', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('nikto')) },
    { id: 'nav-nuclei', label: 'Scan: Nuclei', description: 'Template-based vulnerability detection', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('nuclei')) },
    { id: 'nav-sqlmap', label: 'Scan: SQLMap', description: 'Detect SQL injection issues', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('sqlmap')) },
    { id: 'nav-wpscan', label: 'Scan: WPScan', description: 'WordPress vulnerability auditor', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('wpscan')) },
    { id: 'nav-subdomain', label: 'Scan: Subdomain Discovery', description: 'Passive and active subdomain enumeration', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('subdomain_discovery')) },
    { id: 'nav-metasploit', label: 'Scan: Metasploit', description: 'Payload deployment and exploit framework', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('metasploit')) },
    { id: 'nav-secret-scanner', label: 'Scan: Secret Scanner', description: 'Detection of hardcoded secrets', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('secret_scanner')) },
    { id: 'nav-dir-discovery', label: 'Scan: Directory Discovery', description: 'Fuzzing for hidden files and directories', category: 'Tools', icon: 'travel_explore', action: () => navigate(routePath.scanTool('dir_discovery')) },
    { id: 'action-export-config', label: 'Export Config', description: 'Export current engine configuration', category: 'Actions', icon: 'file_download', action: () => navigate(routes.settings) },
  ], [navigate, theme, setTheme])

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    if (!q) return commands
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(q) ||
        cmd.description.toLowerCase().includes(q) ||
        cmd.category.toLowerCase().includes(q),
    )
  }, [commands, query])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setActiveIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  const execute = useCallback((cmd: Command) => {
    cmd.action()
    onClose()
  }, [onClose])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((prev) => Math.min(prev + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((prev) => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter' && filtered[activeIndex]) {
      e.preventDefault()
      execute(filtered[activeIndex])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }, [filtered, activeIndex, execute, onClose])

  useEffect(() => {
    if (!isOpen) return
    const el = listRef.current?.children[activeIndex] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex, isOpen])

  const grouped = useMemo(() => {
    const groups: Record<string, Command[]> = {}
    for (const cmd of filtered) {
      if (!groups[cmd.category]) groups[cmd.category] = []
      groups[cmd.category].push(cmd)
    }
    return groups
  }, [filtered])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className="relative w-full max-w-xl bg-charcoal border-4 border-black shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] overflow-hidden"
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          >
            <div className="border-b-4 border-black">
              <div className="flex items-center gap-4 px-6 py-4">
                <span className="material-symbols-outlined text-silver/40 text-sm" aria-hidden="true">search</span>
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent text-sm font-mono text-silver-bright placeholder:text-silver/30 focus:outline-none uppercase tracking-wider"
                  autoComplete="off"
                  spellCheck={false}
                  role="combobox"
                  aria-expanded="true"
                  aria-controls="command-list"
                  aria-activedescendant={filtered[activeIndex] ? `cmd-${filtered[activeIndex].id}` : undefined}
                />
                <kbd className="text-[9px] font-black uppercase tracking-widest text-silver/30 border border-black px-2 py-1 bg-charcoal-dark">esc</kbd>
              </div>
            </div>

            <div
              ref={listRef}
              id="command-list"
              role="listbox"
              className="max-h-80 overflow-y-auto"
            >
              {filtered.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-[10px] font-black uppercase tracking-widest text-silver/40">No matching commands</p>
                </div>
              ) : (
                Object.entries(grouped).map(([category, cmds]) => (
                  <div key={category}>
                    <div className="px-6 py-3 text-[9px] font-black uppercase tracking-[0.3em] text-silver/20 border-b border-black bg-charcoal-dark">
                      {category}
                    </div>
                    {cmds.map((cmd, idx) => {
                      const globalIdx = filtered.indexOf(cmd)
                      return (
                        <div
                          key={cmd.id}
                          id={`cmd-${cmd.id}`}
                          role="option"
                          aria-selected={globalIdx === activeIndex}
                          onClick={() => execute(cmd)}
                          onMouseEnter={() => setActiveIndex(globalIdx)}
                          className={`flex items-center gap-4 px-6 py-4 cursor-pointer border-b border-black/30 transition-colors ${
                            globalIdx === activeIndex
                              ? 'bg-rag-blue/20 text-silver-bright border-l-4 border-l-rag-blue'
                              : 'text-silver/70 hover:bg-charcoal-dark hover:text-silver-bright'
                          }`}
                        >
                          <span className="material-symbols-outlined text-sm shrink-0" aria-hidden="true">{cmd.icon}</span>
                          <div className="flex-1 min-w-0">
                            <div className="text-[11px] font-black uppercase tracking-wider">{cmd.label}</div>
                            <div className="text-[9px] text-silver/40 uppercase tracking-widest truncate">{cmd.description}</div>
                          </div>
                          {cmd.shortcut && (
                            <kbd className="text-[8px] font-black uppercase tracking-widest text-silver/20 border border-black px-1.5 py-0.5 shrink-0">{cmd.shortcut}</kbd>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
