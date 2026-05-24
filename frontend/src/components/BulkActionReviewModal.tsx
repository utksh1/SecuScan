import { useEffect, useRef } from "react";

interface BulkActionReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  actionLabel?: string;
  selectedCount?: number;
}

export default function BulkActionReviewModal({
  isOpen,
  onClose,
  onConfirm,
  actionLabel = "Delete",
  selectedCount = 0,
}: BulkActionReviewModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Auto-focus Cancel button when modal opens (safer for destructive actions)
  useEffect(() => {
    if (isOpen) cancelRef.current?.focus();
  }, [isOpen]);

  // Keyboard: Escape closes, Tab traps focus inside modal
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
    if (e.key === "Tab") {
      const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  if (!isOpen) return null;

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      aria-hidden="true"
      onClick={onClose}
    >
      {/* Dialog Box */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-action-title"
        aria-describedby="bulk-action-desc"
        ref={modalRef}
        onKeyDown={handleKeyDown}
        onClick={(e) => e.stopPropagation()}
        className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 w-full max-w-md mx-4"
      >
        {/* Title */}
        <h2
          id="bulk-action-title"
          className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
        >
          Confirm {actionLabel}
        </h2>

        {/* Description */}
        <p
          id="bulk-action-desc"
          className="text-sm text-gray-600 dark:text-gray-300 mb-6"
        >
          You are about to <strong>{actionLabel.toLowerCase()}</strong>{" "}
          <strong>
            {selectedCount} item{selectedCount !== 1 ? "s" : ""}
          </strong>
          . This action <strong>cannot be undone</strong>.
        </p>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3">
          <button
            ref={cancelRef}
            onClick={onClose}
            className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 
                       hover:bg-gray-100 dark:border-gray-600 dark:text-gray-200 
                       dark:hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            aria-label={`Confirm ${actionLabel} of ${selectedCount} items`}
            className="px-4 py-2 rounded-md bg-red-600 text-white 
                       hover:bg-red-700 focus:outline-none focus:ring-2 
                       focus:ring-red-500 focus:ring-offset-2 transition-colors"
          >
            Yes, {actionLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
