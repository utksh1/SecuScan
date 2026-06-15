import React from 'react'
import { Link } from 'react-router-dom'
import { routes } from '../routes'

const faqs = [
  {
    q: 'How do I connect the frontend to the backend?',
    a: 'On first launch, run `cat backend/data/.api_key` to retrieve your API key, then paste it into the "Connect to SecuScan" screen.',
  },
  {
    q: 'Why do I see "Binary not found in PATH" warnings on startup?',
    a: 'Many plugins (Nmap, Nuclei, Subfinder, etc.) wrap external CLI tools. These warnings just mean the corresponding binary is not installed — the plugin still loads but won\'t run until the tool is installed and available in PATH.',
  },
  {
    q: 'Where is my scan data stored?',
    a: 'All findings, tasks, and reports are stored in a local SQLite database under backend/data/. No data leaves your machine unless you export reports manually.',
  },
  {
    q: 'How do I report a bug or request a feature?',
    a: 'Open an issue on the project\'s GitHub repository with details about your environment, steps to reproduce, and expected behavior.',
  },
  {
    q: 'Is it safe to run exploitation plugins (SQLi Exploiter, Sniper, etc.)?',
    a: 'Only run these against targets you own or have explicit authorization to test. See the Terms of Service for details.',
  },
]

export default function Support() {
  return (
    <div className="min-h-screen bg-charcoal-dark px-8 py-12 max-w-4xl mx-auto">
      <header className="mb-10 border-b border-accent-silver/10 pb-6">
        <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-4">
          HELP CENTER
        </div>
        <h1 className="text-4xl text-silver-bright font-bold tracking-tight">Support</h1>
        <p className="text-sm text-silver/60 mt-2">
          Frequently asked questions and ways to get help with SecuScan Workspace.
        </p>
      </header>

      <section className="mb-12">
        <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright mb-6 flex items-center gap-3">
          <span className="w-2 h-2 border border-accent-silver/40 rotate-45" />
          Frequently Asked Questions
        </h2>
        <div className="divide-y divide-accent-silver/5 bg-charcoal/30 border border-accent-silver/5">
          {faqs.map((item) => (
            <div key={item.q} className="p-6">
              <h3 className="text-sm font-semibold text-silver-bright mb-2">{item.q}</h3>
              <p className="text-sm text-silver/70 leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright mb-6 flex items-center gap-3">
          <span className="w-2 h-2 border border-accent-silver/40 rotate-45" />
          Contact &amp; Resources
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <a
            href="https://github.com/utksh1/SecuScan/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="bg-charcoal p-6 border border-accent-silver/5 hover:border-accent-silver/20 transition-all block"
          >
            <h3 className="text-sm font-bold text-silver-bright mb-2">Report an Issue</h3>
            <p className="text-[10px] text-silver/60 uppercase tracking-widest font-mono">
              GitHub Issues →
            </p>
          </a>
          <Link
            to={routes.docs}
            className="bg-charcoal p-6 border border-accent-silver/5 hover:border-accent-silver/20 transition-all block"
          >
            <h3 className="text-sm font-bold text-silver-bright mb-2">Read the Documentation</h3>
            <p className="text-[10px] text-silver/60 uppercase tracking-widest font-mono">
              Docs →
            </p>
          </Link>
        </div>
      </section>

      <div className="pt-6 border-t border-accent-silver/10">
        <Link
          to={routes.dashboard}
          className="text-[10px] font-bold text-silver/50 hover:text-silver-bright uppercase tracking-[0.2em] transition-colors"
        >
          ← Back to Dashboard
        </Link>
      </div>
    </div>
  )
}

