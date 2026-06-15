
import React from 'react'
import { Link } from 'react-router-dom'
import { routes } from '../routes'

const sections = [
  {
    title: '1. Local-First Architecture',
    content:
      'SecuScan Workspace is designed to run primarily on your local machine or private infrastructure. Scan data, findings, and reports are stored in your own database and are not transmitted to any third-party server operated by SecuScan.',
  },
  {
    title: '2. API Key Storage',
    content:
      'Your backend API key is stored only in your browser\'s localStorage under the key "secuscan_api_key" and is sent as the X-Api-Key header on every API request to your own backend instance. It is never transmitted to any third party or stored on any external server.',
  },
  {
    title: '3. Data We Process',
    content:
      'When you run scans, SecuScan processes data about the targets you specify (domains, IPs, URLs) and stores resulting findings, task logs, and reports in your local database. This data remains under your control at all times.',
  },
  {
    title: '4. Third-Party Tools & Plugins',
    content:
      'Some plugins (e.g. Subfinder, Nuclei, Nmap) may make outbound network requests to the targets you configure. SecuScan does not share scan results with these tool vendors; they are invoked locally as subprocesses.',
  },
  {
    title: '5. Cookies & Tracking',
    content:
      'SecuScan Workspace does not use cookies, analytics, or tracking scripts. No usage data is collected or sent to external analytics providers.',
  },
  {
    title: '6. Data Retention & Deletion',
    content:
      'Findings, scan history, and reports remain in your local database until you delete them via the Registry or database directly. Deleting data is a one-way action and SecuScan does not retain backups on your behalf.',
  },
  {
    title: '7. Changes to This Policy',
    content:
      'This policy may be updated as SecuScan evolves. Continued use of the workspace after changes constitutes acceptance of the revised policy.',
  },
  {
    title: '8. Contact',
    content:
      'For questions about this Privacy Policy, please open an issue on the project\'s GitHub repository or reach out via the Support page.',
  },
]

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-charcoal-dark px-8 py-12 max-w-4xl mx-auto">
      <header className="mb-10 border-b border-accent-silver/10 pb-6">
        <div className="bg-rag-amber text-black px-4 py-1 text-xs uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-4">
          LEGAL
        </div>
        <h1 className="text-4xl text-silver-bright font-bold tracking-tight">Privacy Policy</h1>
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
          â† Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
