import React, { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTheme } from '../components/ThemeContext'
import { routes } from '../routes'

export default function NotFound() {
  const { theme } = useTheme()
  const isLight = theme === 'light'

  useEffect(() => {
    document.title = '404 - Page Not Found | SecuScan'
  }, [])

  return (
    <div className={`min-h-[75vh] flex items-center justify-center p-6 ${isLight ? 'bg-zinc-50' : 'bg-charcoal-dark'}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className={`w-full max-w-lg border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] relative overflow-hidden ${
          isLight ? 'bg-zinc-100' : 'bg-charcoal'
        }`}
      >
        {/* Reuse the existing scanline animation class from index.css */}
        <div className="login-scanline" />

        {/* Top border decoration */}
        <div className="absolute top-0 inset-x-0 h-1 bg-rag-red" />

        {/* Content */}
        <div className="flex flex-col items-center text-center space-y-6 relative z-10">
          {/* SecuScan Branding inside the 404 card */}
          <div className="bg-rag-amber text-black px-3 py-0.5 text-[9px] font-black uppercase tracking-widest inline-block shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] font-mono">
            SecuScan // Security
          </div>

          {/* Warning Icon Badge */}
          <div className={`w-16 h-16 flex items-center justify-center border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] ${
            isLight ? 'bg-zinc-200' : 'bg-charcoal-dark'
          }`}>
            <span className="material-symbols-outlined text-4xl text-rag-red animate-pulse">
              gpp_bad
            </span>
          </div>

          {/* Error Code & Headings Hierarchy */}
          <div className="space-y-3">
            <h1 className={`text-7xl font-mono font-black tracking-tighter ${
              isLight ? 'text-zinc-900' : 'text-silver-bright'
            } animate-glitch`}>
              404
            </h1>

            <h2 className={`text-2xl font-bold uppercase tracking-wide ${
              isLight ? 'text-zinc-800' : 'text-silver-bright'
            }`}>
              Page Not Found
            </h2>

            <h3 className={`text-[10px] font-mono font-bold uppercase tracking-[0.2em] italic ${
              isLight ? 'text-zinc-500' : 'text-silver/50'
            }`}>
              Perimeter Breach // Mismatch
            </h3>
          </div>

          {/* Divider line */}
          <div className="w-full h-1 bg-black/10" />

          {/* Explanation Message */}
          <p className={`text-xs font-mono uppercase tracking-widest leading-relaxed ${
            isLight ? 'text-zinc-600' : 'text-silver/60'
          }`}>
            The requested page does not exist or has been relocated outside the mapped perimeter matrix. Verification failed. Access denied or target route is not configured.
          </p>

          {/* Action Button */}
          <Link
            to={routes.dashboard}
            className="w-full sm:w-auto inline-block text-center bg-rag-blue hover:bg-rag-blue/90 text-black px-8 py-3 text-[10px] font-black uppercase tracking-[0.3em] border-4 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all italic"
          >
            Return to Dashboard
          </Link>
        </div>
      </motion.div>
    </div>
  )
}
