'use client';

import { useEffect, useRef } from 'react';
import { AlertTriangle, Trash2, ShieldAlert } from 'lucide-react';
import { Button } from './Button';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

const iconMap = {
  danger: Trash2,
  warning: AlertTriangle,
  default: ShieldAlert,
};

const iconBgMap = {
  danger: 'bg-red-100 dark:bg-red-900/30',
  warning: 'bg-amber-100 dark:bg-amber-900/30',
  default: 'bg-blue-100 dark:bg-blue-900/30',
};

const iconColorMap = {
  danger: 'text-red-600 dark:text-red-400',
  warning: 'text-amber-600 dark:text-amber-400',
  default: 'text-blue-600 dark:text-blue-400',
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      cancelRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onCancel]);

  if (!open) return null;

  const Icon = iconMap[variant];
  const buttonVariant = variant === 'danger' ? 'danger' : 'primary';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in"
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-md w-full mx-4 animate-scale-in border border-gray-200 dark:border-gray-700"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div className={`shrink-0 rounded-full p-3 ${iconBgMap[variant]}`}>
              <Icon className={`w-6 h-6 ${iconColorMap[variant]}`} />
            </div>
            <div className="flex-1 min-w-0">
              <h3
                id="confirm-title"
                className="text-lg font-semibold text-gray-900 dark:text-gray-100"
              >
                {title}
              </h3>
              <p
                id="confirm-message"
                className="mt-2 text-sm text-gray-600 dark:text-gray-400"
              >
                {message}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-2xl">
          <Button
            ref={cancelRef}
            variant="secondary"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={buttonVariant}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Processing...' : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
