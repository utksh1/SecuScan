import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { routes } from '../routes'

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
                setTimeout(() => navigate(routes.dashboard), 800)
            } else {
                setStatus('denied')
                setTimeout(() => setStatus('ready'), 2000)
            }
        }, 1500)
    }

    return (
        <div className="min-h-screen bg-charcoal-dark flex items-center justify-center p-6 relative overflow-hidden font-mono selection:bg-rag-blue selection:text-black">
            {/* Background Text Noise */}
            <div className="absolute inset-0 flex flex-col justify-between p-12 pointer-events-none select-none overflow-hidden opacity-5">
                <div className="text-[200px] font-black italic uppercase leading-none truncate w-[150%]">SECUSCAN</div>
                <div className="text-[200px] font-black italic uppercase leading-none truncate w-[150%] -translate-x-1/4">TERMINAL</div>
            </div>

            <div className={`w-full max-w-[500px] bg-charcoal border-4 border-black shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] p-8 md:p-12 relative z-10 transition-all duration-300 ${
                status === 'denied' ? 'animate-shake translate-x-1 border-rag-red' : 
                status === 'granted' ? 'scale-105 border-rag-green shadow-[0px_0px_0px_0px_rgba(0,0,0,1)] translate-x-[12px] translate-y-[12px]' : ''
            }`}>
                 {/* Header Section */}
                <header className="space-y-6 mb-12 border-b-4 border-black pb-8">
                    <div className="bg-silver-bright text-black px-4 py-1 text-[10px] font-black uppercase tracking-[0.3em] inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                        Clearance_Protocol_772
                    </div>
                    <h1 className="text-6xl font-black text-silver-bright italic tracking-tighter uppercase leading-none">
                        AUTH<span className="text-rag-blue border-b-8 border-rag-blue inline-block mb-2">_</span>
                    </h1>
                </header>

                {/* Form Section */}
                <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="space-y-6">
                        {/* Username */}
                        <div className="space-y-2 group">
                            <label className={`text-xs font-black uppercase tracking-[0.2em] italic flex items-center gap-2 transition-colors ${
                                focusedField === 'username' ? 'text-rag-blue' : 'text-silver/40'
                            }`}>
                                <span className="material-symbols-outlined text-sm font-black">person</span> Operator_ID
                            </label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                onFocus={() => setFocusedField('username')}
                                onBlur={() => setFocusedField(null)}
                                className={`w-full bg-charcoal-dark border-4 p-4 text-sm text-silver-bright focus:outline-none placeholder:text-silver/20 italic font-mono uppercase transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,0.5)] ${
                                    focusedField === 'username' ? 'border-rag-blue shadow-none translate-x-[2px] translate-y-[2px]' : 'border-black'
                                }`}
                                placeholder="ENTER_IDENTITY..."
                                disabled={status !== 'ready'}
                                autoComplete="off"
                            />
                        </div>

                        {/* Password */}
                        <div className="space-y-2 group">
                            <label className={`text-xs font-black uppercase tracking-[0.2em] italic flex items-center gap-2 transition-colors ${
                                focusedField === 'password' ? 'text-rag-amber' : 'text-silver/40'
                            }`}>
                                <span className="material-symbols-outlined text-sm font-black">key</span> Access_Cipher
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                onFocus={() => setFocusedField('password')}
                                onBlur={() => setFocusedField(null)}
                                className={`w-full bg-charcoal-dark border-4 p-4 text-sm tracking-widest text-silver-bright focus:outline-none placeholder:text-silver/20 italic font-mono transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,0.5)] ${
                                    focusedField === 'password' ? 'border-rag-amber shadow-none translate-x-[2px] translate-y-[2px]' : 'border-black'
                                }`}
                                placeholder="••••••••••••"
                                disabled={status !== 'ready'}
                            />
                        </div>
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        className={`w-full py-6 text-sm font-black uppercase tracking-[0.3em] italic border-4 transition-all relative overflow-hidden flex items-center justify-center shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] ${
                            status === 'ready' ? 'bg-silver-bright border-black text-black hover:bg-white hover:-translate-y-1 hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,1)] active:translate-y-2 active:translate-x-2 active:shadow-none' : 
                            status === 'granted' ? 'bg-rag-green border-black text-black shadow-none translate-x-[6px] translate-y-[6px]' : 
                            status === 'denied' ? 'bg-rag-red border-black text-black shadow-none translate-x-[6px] translate-y-[6px]' : 'bg-charcoal border-black text-silver/20 cursor-not-allowed shadow-none'
                        }`}
                        disabled={status !== 'ready'}
                    >
                        <span className="relative z-10 flex items-center gap-3">
                            {status === 'ready' && <><span className="material-symbols-outlined font-black">login</span> ENGAGE_SYSTEM</>}
                            {status === 'processing' && <><span className="material-symbols-outlined font-black animate-spin">sync</span> VALIDATING...</>}
                            {status === 'granted' && <><span className="material-symbols-outlined font-black">check_circle</span> ACCESS_GRANTED</>}
                            {status === 'denied' && <><span className="material-symbols-outlined font-black">error</span> ACCESS_DENIED</>}
                        </span>
                    </button>
                </form>

                {/* Footer Status */}
                <footer className="mt-8 pt-8 border-t-4 border-black">
                    <div className="flex justify-between items-center text-[10px] font-black uppercase font-mono tracking-[0.2em] italic">
                         <div className="flex gap-2 items-center">
                            <span className={`w-3 h-3 border-2 border-black inline-block ${
                                status === 'granted' ? 'bg-rag-green' : 
                                status === 'denied' ? 'bg-rag-red animate-pulse' : 
                                status === 'processing' ? 'bg-rag-amber animate-pulse' : 'bg-rag-blue'
                            }`}></span>
                            <span className={status === 'denied' ? 'text-rag-red' : status === 'granted' ? 'text-rag-green' : 'text-silver/40'}>
                                {status === 'ready' && 'TERMINAL_STANDBY'}
                                {status === 'processing' && 'UPLINK_ACTIVE'}
                                {status === 'granted' && 'SECURITY_CLEARED'}
                                {status === 'denied' && 'FATAL_HANDSHAKE'}
                            </span>
                         </div>
                         <span className="text-silver/20 bg-black px-2 py-1">v2.4_AUTH</span>
                    </div>
                </footer>
            </div>
        </div>
    )
}
