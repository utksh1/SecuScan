import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info';
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  type = 'warning',
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Focus trap and keyboard handling
  useEffect(() => {
    if (!isOpen) return;

    // Store previously focused element
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Focus the confirm button
    confirmButtonRef.current?.focus();

    // Handle keyboard events
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      } else if (e.key === 'Enter' && !e.shiftKey) {
        // Only trigger onConfirm if the active element is NOT a button
        // (buttons already handle Enter via their onClick)
        const activeElement = document.activeElement;
        if (activeElement?.tagName !== 'BUTTON') {
          e.preventDefault();
          onConfirm();
        }
      } else if (e.key === 'Tab') {
        const focusableElements = modalRef.current?.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        if (focusableElements && focusableElements.length > 0) {
          const firstElement = focusableElements[0] as HTMLElement;
          const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [isOpen, onConfirm, onCancel]);

  // Lock body scroll when modal opens
  useEffect(() => {
    if (!isOpen) return;

    const originalOverflow = document.body.style.overflow;
    const originalPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${scrollbarWidth}px`;

    return () => {
      document.body.style.overflow = originalOverflow;
      document.body.style.paddingRight = originalPaddingRight;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const getButtonStyle = () => {
    switch (type) {
      case 'danger': return 'bg-rag-red hover:bg-rag-red/80';
      case 'warning': return 'bg-rag-amber hover:bg-rag-amber/80';
      default: return 'bg-rag-blue hover:bg-rag-blue/80';
    }
  };

  // Render modal using Portal - goes OUTSIDE #root
  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal - Neo-brutalist style */}
      <div
        ref={modalRef}
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
      >
        <div className="bg-charcoal border-4 border-black shadow-[12px_12px_0px_0px_rgba(0,0,0,1)]">
          {/* Header */}
          <div className="border-b-4 border-black p-6">
            <h2 id="modal-title" className="text-xl font-black uppercase tracking-wider text-silver-bright">
              {title}
            </h2>
          </div>

          {/* Body */}
          <div className="p-6">
            <p id="modal-description" className="text-sm font-mono text-silver-bright/70 leading-relaxed">
              {message}
            </p>
          </div>

          {/* Footer */}
          <div className="border-t-4 border-black p-6 flex justify-end gap-4">
            <button
              onClick={onCancel}
              className="px-6 py-3 bg-charcoal-dark border-2 border-black text-xs font-black uppercase tracking-wider text-silver-bright/60 hover:text-silver-bright hover:border-silver-bright/30 transition-all"
            >
              {cancelText}
            </button>
            <button
              ref={confirmButtonRef}
              onClick={onConfirm}
              className={`px-6 py-3 ${getButtonStyle()} border-2 border-black text-black text-xs font-black uppercase tracking-wider shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-0.5 active:translate-y-0.5 transition-all`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body
  );
};
