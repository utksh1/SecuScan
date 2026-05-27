import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
      if (e.key === "Enter") onConfirm();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, onConfirm, onCancel]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          style={{ backgroundColor: "rgba(0,0,0,0.75)" }}
          onClick={onCancel}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: 10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="bg-charcoal border-4 border-black shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] w-full max-w-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`border-b-4 border-black px-8 py-6 ${danger ? "bg-rag-red/10" : "bg-charcoal-dark"}`}>
              <div className="flex items-center gap-4">
                <span className={`material-symbols-outlined text-2xl ${danger ? "text-rag-red" : "text-rag-amber"}`}>
                  {danger ? "warning" : "info"}
                </span>
                <h2 className="text-sm font-black text-silver-bright uppercase tracking-widest italic">
                  {title}
                </h2>
              </div>
            </div>
            <div className="px-8 py-8">
              <p className="text-xs font-mono text-silver/60 leading-relaxed uppercase tracking-wide">
                {message}
              </p>
            </div>
            <div className="border-t-4 border-black px-8 py-6 flex items-center justify-end gap-4">
              <button
                onClick={onCancel}
                className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-silver/40 hover:text-silver transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className={`px-8 py-3 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center gap-3 italic ${
                  danger ? "bg-rag-red text-black" : "bg-rag-blue text-black"
                }`}
              >
                {confirmLabel}
                <span className="material-symbols-outlined text-sm">
                  {danger ? "delete_forever" : "check"}
                </span>
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
