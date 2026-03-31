import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react';

interface AlertProps {
  type: 'error' | 'success' | 'warning' | 'info';
  message: string;
  onClose?: () => void;
}

export function Alert({ type, message, onClose }: AlertProps) {
  const icons = {
    error: XCircle,
    success: CheckCircle,
    warning: AlertCircle,
    info: Info,
  };

  const colors = {
    error: 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800',
    success: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
    warning: 'bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800',
    info: 'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 border-blue-200 dark:border-blue-800',
  };

  const Icon = icons[type];

  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl border animate-fade-in ${colors[type]}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <p className="flex-1 text-sm">{message}</p>
      {onClose && (
        <button
          onClick={onClose}
          className="text-current hover:opacity-70 transition-opacity"
          aria-label="Dismiss alert"
        >
          <XCircle className="w-5 h-5" />
        </button>
      )}
    </div>
  );
}
