import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
    const navigate = useNavigate()
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [status, setStatus] = useState<'ready' | 'processing' | 'granted' | 'denied'>('ready')
    const [focusedField, setFocusedField] = useState<'username' | 'password' | null>(null)

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        setStatus('processing')

        // Simulate tactical handshake
        setTimeout(() => {
            if (username && password) {
                setStatus('granted')
                setTimeout(() => navigate('/dashboard'), 800)
            } else {
                setStatus('denied')
                setTimeout(() => setStatus('ready'), 2000)
            }
        }, 1500)
    }

    return (
        <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-6 relative overflow-hidden font-mono selection:bg-rag-blue/30 selection:text-white">
            {/* Tactical Grid Background */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
                 style={{ backgroundImage: 'linear-gradient(var(--accent-silver) 1px, transparent 1px), linear-gradient(90deg, var(--accent-silver) 1px, transparent 1px)', backgroundSize: '100px 100px' }}>
            </div>
            
            {/* Side Geometric Accents */}
            <div className="absolute left-10 top-1/2 -translate-y-1/2 w-1 h-32 bg-accent-silver/5 hidden lg:block"></div>
            <div className="absolute right-10 top-1/2 -translate-y-1/2 w-1 h-32 bg-accent-silver/5 hidden lg:block"></div>

            <div className={`w-full max-w-[500px] border border-accent-silver/10 bg-charcoal p-1 shadow-2xl transition-all duration-700 ${
                status === 'denied' ? 'animate-shake border-rag-red/40 shadow-rag-red/20' : 
                status === 'granted' ? 'scale-105 border-rag-green/40 shadow-rag-green/20' : ''
            }`}>
                <div className="border border-accent-silver/5 p-12 space-y-12">
                     {/* Header Section */}
                    <header className="space-y-6 text-center">
                        <div className="inline-block px-4 py-1 border border-accent-silver/10 text-[8px] font-black uppercase tracking-[0.6em] text-silver/20 mb-4 italic">
                            Clearance_Protocol_772
                        </div>
                        <h1 className="text-5xl font-serif font-light text-silver-bright tracking-tighter italic leading-none select-none">
                            SECUSCAN<span className="text-rag-blue">.</span>
                        </h1>
                        <p className="text-[10px] text-silver/20 uppercase tracking-[0.4em] italic mt-2">Core_Intelligence_Terminal</p>
                    </header>

                    {/* Form Section */}
                    <form onSubmit={handleSubmit} className="space-y-8">
                        <div className="space-y-6">
                            {/* Username */}
                            <div className="space-y-3">
                                <label className="text-[9px] font-bold uppercase tracking-widest text-silver/30 italic block px-1">Operator_Identity</label>
                                <div className={`relative border p-1 transition-all duration-300 ${
                                    focusedField === 'username' ? 'border-rag-blue/40 bg-white/5' : 'border-accent-silver/10'
                                }`}>
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        onFocus={() => setFocusedField('username')}
                                        onBlur={() => setFocusedField(null)}
                                        className="w-full bg-transparent p-4 text-xs text-silver-bright focus:outline-none placeholder:text-silver/5 italic font-mono"
                                        placeholder="Enter_User_ID"
                                        disabled={status !== 'ready'}
                                        autoComplete="off"
                                    />
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-20">
                                        <span className="material-symbols-outlined text-sm">person</span>
                                    </div>
                                </div>
                            </div>

                            {/* Password */}
                            <div className="space-y-3">
                                <label className="text-[9px] font-bold uppercase tracking-widest text-silver/30 italic block px-1">Access_Cipher</label>
                                <div className={`relative border p-1 transition-all duration-300 ${
                                    focusedField === 'password' ? 'border-rag-blue/40 bg-white/5' : 'border-accent-silver/10'
                                }`}>
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        onFocus={() => setFocusedField('password')}
                                        onBlur={() => setFocusedField(null)}
                                        className="w-full bg-transparent p-4 text-xs text-silver-bright focus:outline-none placeholder:text-silver/5 italic font-mono"
                                        placeholder="············"
                                        disabled={status !== 'ready'}
                                    />
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-20">
                                        <span className="material-symbols-outlined text-sm">key</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            className={`w-full py-6 text-[11px] font-black uppercase tracking-[0.5em] italic transition-all relative overflow-hidden flex items-center justify-center ${
                                status === 'ready' ? 'bg-silver-bright text-charcoal-dark hover:bg-white active:scale-95' : 
                                status === 'granted' ? 'bg-rag-green text-white' : 
                                status === 'denied' ? 'bg-rag-red text-white' : 'bg-charcoal border border-accent-silver/10 text-silver/20'
                            }`}
                            disabled={status !== 'ready'}
                        >
                            <span className="relative z-10">
                                {status === 'ready' && 'Engage_System'}
                                {status === 'processing' && 'Validating_Cipher...'}
                                {status === 'granted' && 'Access_Granted'}
                                {status === 'denied' && 'Access_Denied'}
                            </span>
                            {status === 'processing' && (
                                <div className="absolute inset-0 bg-white/10 animate-pulse"></div>
                            )}
                        </button>
                    </form>

                    {/* Footer Status */}
                    <footer className="pt-8 border-t border-accent-silver/5">
                        <div className="flex justify-between items-center opacity-40">
                             <div className="flex gap-2 items-center">
                                <div className={`w-1.5 h-1.5 rounded-full ${
                                    status === 'granted' ? 'bg-rag-green' : 
                                    status === 'denied' ? 'bg-rag-red' : 
                                    status === 'processing' ? 'bg-rag-amber' : 'bg-rag-blue'
                                } shadow-[0_0_8px] shadow-current transition-colors duration-500`}></div>
                                <span className="text-[8px] uppercase font-black tracking-widest italic font-mono">
                                    {status === 'ready' && 'Terminal_Online'}
                                    {status === 'processing' && 'Uplink_Active'}
                                    {status === 'granted' && 'Credential_Success'}
                                    {status === 'denied' && 'Fatal_Handshake_Error'}
                                </span>
                             </div>
                             <span className="text-[8px] text-silver/10 uppercase tracking-widest italic font-mono">v1.0.2_AUTH</span>
                        </div>
                    </footer>
                </div>
            </div>

            {/* Background Text Noise */}
            <div className="fixed bottom-10 left-10 text-[8px] font-black text-white/5 uppercase tracking-[2em] select-none pointer-events-none hidden lg:block">
                Secure_Handshake_Active
            </div>
            <div className="fixed top-10 right-10 text-[8px] font-black text-white/5 uppercase tracking-[2em] select-none pointer-events-none hidden lg:block">
                No_Unauthorized_Probing
            </div>
        </div>
    )
}
