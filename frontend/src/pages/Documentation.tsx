import React from 'react'
import { Link } from 'react-router-dom'
import { routes } from '../routes'

const gettingStarted = [
  'Clone the repository and install dependencies for both backend (`pip install -r requirements.txt`) and frontend (`npm install`).',
  'Start the backend: `uvicorn secuscan.main:app --reload` (runs on port 8000).',
  'Start the frontend: `npm run dev` (runs on port 5173).',
  'Retrieve your API key: `cat backend/data/.api_key`, then paste it into the connection screen.',
]

const modules = [
  { name: 'Dashboard', desc: 'Central overview of vulnerabilities, scan cycles, and recent audit findings.' },
  { name: 'Registry', desc: 'History of all scans and tasks executed across targets.' },
  { name: 'Findings', desc: 'Detailed list of vulnerabilities with severity, target, and risk scoring.' },
  { name: 'Reports', desc: 'Generate and export PDF/HTML reports summarizing findings.' },
  { name: 'Workflows', desc: 'Chain multiple plugins together into automated scan pipelines.' },
  { name: 'Toolkit', desc: 'Browse and configure the 60+ available scanning plugins.' },
]

const pluginCategories = [
  { name: 'Reconnaissance', examples: 'Subfinder, Subdomain Finder, DNS Recon, Domain Finder, theHarvester' },
  { name: 'Network', examples: 'Nmap (Port Scanner, Network Scanner), ICMP Ping, dnsx' },
  { name: 'Web Application', examples: 'Nikto, Crawler (Katana), Directory Discovery (ffuf), HTTP Inspector' },
  { name: 'Vulnerability Scanning', examples: 'Nuclei (Template Vulnerability Scan), WAF Detector, TLS Security Analysis' },
  { name: 'Exploitation', examples: 'SQLi Exploiter, XSS Exploiter, Sniper Auto-Exploiter (use with caution)' },
  { name: 'Cloud & Container', examples: 'Cloud Scanner, S3/Blob Auditor, Container Scan (Trivy), K8s Scanner, IaC Scanner (Checkov)' },
  { name: 'CMS Scanners', examples: 'WordPress Security Scan, Joomla Security Scan, Drupal Security Scan' },
]

export default function Documentation() {
  return (
    <div className="min-h-screen bg-charcoal-dark px-8 py-12 max-w-4xl mx-auto">
      <header className="mb-10 border-b border-accent-silver/10 pb-6">
        <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-4">
          DOCS
        </div>
        <h1 className="text-4xl text-silver-bright font-bold tracking-tight">Documentation</h1>
        <p className="text-sm text-silver/60 mt-2">
          Everything you need to set up, navigate, and operate SecuScan Workspace.
        </p>
      </header>

      <section className="mb-12">
        <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright mb-6 flex items-center gap-3">
          <span className="w-2 h-2 border border-accent-silver/40 rotate-45" />
          Getting Started
        </h2>
        <ol className="space-y-3">
          {gettingStarted.map((step, i) => (
            <li key={i} className="flex gap-4 bg-charcoal/30 p-4 border border-accent-silver/5">
              <span className="text-rag-blue font-mono text-sm font-bold">{(i + 1).toString().padStart(2, '0')}</span>
              <p className="text-sm text-silver/70 leading-relaxed">{step}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mb-12">
        <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright mb-6 flex items-center gap-3">
          <span className="w-2 h-2 border border-accent-silver/40 rotate-45" />
          Core Modules
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {modules.map((m) => (
            <div key={m.name} className="bg-charcoal p-6 border border-accent-silver/5">
              <h3 className="text-sm font-bold text-silver-bright mb-2 uppercase tracking-widest">{m.name}</h3>
              <p className="text-sm text-silver/70 leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright mb-6 flex items-center gap-3">
          <span className="w-2 h-2 border border-accent-silver/40 rotate-45" />
          Plugin Categories
        </h2>
        <div className="divide-y divide-accent-silver/5 bg-charcoal/30 border border-accent-silver/5">
          {pluginCategories.map((cat) => (
            <div key={cat.name} className="p-6">
              <h3 className="text-sm font-bold text-silver-bright mb-1 uppercase tracking-widest">{cat.name}</h3>
              <p className="text-[11px] text-silver/60 font-mono uppercase tracking-wider">{cat.examples}</p>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-silver/40 uppercase tracking-[0.2em] mt-4">
          Note: Most plugins wrap external CLI tools (Nmap, Nuclei, etc.) and require those binaries to be installed and available in PATH.
        </p>
      </section>

      <div className="pt-6 border-t border-accent-silver/10">
        <Link
          to={routes.dashboard}
          className="text-[10px] font-bold text-silver/50 hover:text-silver-bright uppercase tracking-[0.2em] transition-colors"
        >
          Ã¢â€ Â Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
