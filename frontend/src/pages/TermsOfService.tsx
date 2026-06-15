import React from 'react'
import { Link } from 'react-router-dom'
import { routes } from '../routes'

const sections = [
  {
    title: '1. Acceptance of Terms',
    content:
      'By accessing or using SecuScan Workspace, you agree to be bound by these Terms of Service. If you do not agree, do not use this software.',
  },
  {
    title: '2. Authorized Use Only',
    content:
      'SecuScan is a security testing toolkit. You may only run scans, exploits, or reconnaissance modules against systems, domains, or networks that you own or for which you have obtained explicit, written authorization. Unauthorized scanning of third-party systems may violate computer misuse laws in your jurisdiction.',
  },
  {
    title: '3. No Warranty',
    content:
      'SecuScan Workspace is provided "as is" without warranties of any kind, express or implied, including but not limited to accuracy of findings, fitness for a particular purpose, or non-infringement. Scan results should be independently verified before being relied upon.',
  },
  {
    title: '4. Limitation of Liability',
    content:
      'In no event shall the SecuScan project, its contributors, or maintainers be liable for any damages Ã¢â‚¬â€ including data loss, service disruption, or legal consequences Ã¢â‚¬â€ arising from the use or misuse of this software.',
  },
  {
    title: '5. User Responsibilities',
    content:
      'You are solely responsible for the targets you configure, the plugins you run, and any consequences resulting from scan execution, including but not limited to active exploitation modules (e.g. SQLi Exploiter, XSS Exploiter, Sniper).',
  },
  {
    title: '6. Third-Party Tools',
    content:
      'SecuScan integrates with third-party open-source tools (e.g. Nmap, Nuclei, Subfinder, ZAP). Use of these tools is subject to their respective licenses, and SecuScan is not responsible for their behavior.',
  },
  {
    title: '7. Modifications to Service',
    content:
      'Features, plugins, and APIs may change between versions without notice. Check the Documentation page for the most current capabilities.',
  },
  {
    title: '8. Governing Law',
    content:
      'These terms shall be governed by applicable local laws in the jurisdiction where the SecuScan instance is operated.',
  },
]

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-charcoal-dark px-8 py-12 max-w-4xl mx-auto">
      <header className="mb-10 border-b border-accent-silver/10 pb-6">
        <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-4">
          LEGAL
        </div>
        <h1 className="text-4xl text-silver-bright font-bold tracking-tight">Terms of Service</h1>
        <p className="text-[10px] text-silver/50 uppercase tracking-[0.3em] font-mono mt-2">
          Last updated: June 2026
        </p>
      </header>

      <div className="space-y-8">
        {sections.map((section) => (
          <section key={section.title}>
            <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-silver-bright mb-3 flex items-center gap-3">
              <span className="w-2 h-2 border border-accent-silver/40 rotate-45" />
              {section.title}
            </h2>
            <p className="text-sm text-silver/70 leading-relaxed">{section.content}</p>
          </section>
        ))}
      </div>

      <div className="mt-12 pt-6 border-t border-accent-silver/10">
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
