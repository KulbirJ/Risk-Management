'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (type: ToastType, message: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType>({
  toasts: [],
  addToast: () => {},
  removeToast: () => {},
});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string, duration = 5000) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      setToasts((prev) => [...prev, { id, type, message, duration }]);

      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

const iconMap: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const styleMap: Record<ToastType, string> = {
  success:
    'bg-white dark:bg-gray-800 border-l-4 border-l-emerald-500 text-gray-900 dark:text-gray-100',
  error:
    'bg-white dark:bg-gray-800 border-l-4 border-l-red-500 text-gray-900 dark:text-gray-100',
  warning:
    'bg-white dark:bg-gray-800 border-l-4 border-l-amber-500 text-gray-900 dark:text-gray-100',
  info:
    'bg-white dark:bg-gray-800 border-l-4 border-l-blue-500 text-gray-900 dark:text-gray-100',
};

const iconColorMap: Record<ToastType, string> = {
  success: 'text-emerald-500',
  error: 'text-red-500',
  warning: 'text-amber-500',
  info: 'text-blue-500',
};

const progressColorMap: Record<ToastType, string> = {
  success: 'bg-emerald-500',
  error: 'bg-red-500',
  warning: 'bg-amber-500',
  info: 'bg-blue-500',
};

function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: Toast[];
  onRemove: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div
            key={toast.id}
            className={`${styleMap[toast.type]} rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 animate-slide-in-right pointer-events-auto overflow-hidden`}
            role="alert"
          >
            <div className="flex items-start gap-3 p-4">
              <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${iconColorMap[toast.type]}`} />
              <p className="text-sm flex-1">{toast.message}</p>
              <button
                onClick={() => onRemove(toast.id)}
                className="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                aria-label="Dismiss notification"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            {toast.duration && toast.duration > 0 && (
              <div className="h-0.5 w-full bg-gray-100 dark:bg-gray-700">
                <div
                  className={`h-full ${progressColorMap[toast.type]} animate-progress-fill`}
                  style={{ animationDuration: `${toast.duration}ms` }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
