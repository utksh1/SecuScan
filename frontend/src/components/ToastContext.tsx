import React, { createContext, useContext, useState, ReactNode } from 'react';

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  addToast: (message: string, type?: ToastType) => void;
  removeToast: (id: string) => void;
  toasts: Toast[];
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);

    // Auto-remove after 4 seconds
    setTimeout(() => {
      removeToast(id);
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Visual component to render toasts
export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: 'var(--space-6)',
      right: 'var(--space-6)',
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-3)',
      zIndex: 9999,
    }}>
      {toasts.map((toast) => {
        let bgColor = 'var(--bg-elevated)';
        let borderColor = 'var(--border-default)';
        let icon = 'ℹ️';

        if (toast.type === 'success') {
          borderColor = 'var(--status-success)';
          icon = '✅';
        } else if (toast.type === 'error') {
          borderColor = 'var(--status-danger)';
          icon = '❌';
        }

        return (
          <div key={toast.id} style={{
            background: bgColor,
            borderLeft: `4px solid ${borderColor}`,
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3) var(--space-4)',
            boxShadow: 'var(--shadow-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
            minWidth: '250px',
            maxWidth: '400px',
            animation: 'slideUp var(--transition-fast)',
            borderRight: '1px solid var(--border-default)',
            borderTop: '1px solid var(--border-default)',
            borderBottom: '1px solid var(--border-default)',
          }}>
            <span>{icon}</span>
            <span style={{ flex: 1, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
              {toast.message}
            </span>
            <button
              onClick={() => removeToast(toast.id)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '16px',
                padding: '4px'
              }}
            >
              ×
            </button>
          </div>
        );
      })}
    </div>
  );
}
