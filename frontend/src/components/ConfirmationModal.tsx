import { AnimatePresence, motion } from 'framer-motion'

interface ConfirmationModalProps {
    open: boolean
    title: string
    description: string
    confirmLabel: string
    cancelLabel?: string
    danger?: boolean
    onConfirm: () => void
    onCancel: () => void
}

export default function ConfirmationModal({
    open,
    title,
    description,
    confirmLabel,
    cancelLabel = 'Cancel',
    danger = false,
    onConfirm,
    onCancel
}: ConfirmationModalProps) {
    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-6"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="confirmation-modal-title"
                    onClick={onCancel}
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="w-full max-w-lg border-4 border-black bg-charcoal p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="space-y-4">
                            <div
                                className={`inline-flex px-3 py-1 text-[10px] font-black uppercase tracking-widest border-2 border-black ${
                                    danger
                                        ? 'bg-rag-red text-black'
                                        : 'bg-rag-blue text-black'
                                }`}
                            >
                                Confirmation Required
                            </div>

                            <h2
                                id="confirmation-modal-title"
                                className="text-3xl font-black uppercase text-silver-bright tracking-tight italic"
                            >
                                {title}
                            </h2>

                            <p className="text-sm font-mono text-silver/70 leading-relaxed">
                                {description}
                            </p>
                        </div>

                        <div className="mt-10 flex justify-end gap-4">
                            <button
                                onClick={onCancel}
                                className="px-6 py-3 border-2 border-silver/20 bg-charcoal-dark text-silver text-[10px] font-black uppercase tracking-widest hover:border-silver-bright/40 transition-all"
                            >
                                {cancelLabel}
                            </button>

                            <button
                                autoFocus
                                onClick={onConfirm}
                                className={`px-6 py-3 border-2 border-black text-[10px] font-black uppercase tracking-widest transition-all shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 ${
                                    danger
                                        ? 'bg-rag-red text-black'
                                        : 'bg-rag-blue text-black'
                                }`}
                            >
                                {confirmLabel}
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    )
}