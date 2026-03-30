interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}

export function Badge({ children, variant = 'default', size = 'md' }: BadgeProps) {
  const variantClasses = {
    default: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${variantClasses[variant]} ${sizeClasses[size]}`}
    >
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const colorMap: Record<string, string> = {
    Critical: 'bg-red-600 text-white',
    High:     'bg-amber-500 text-white',
    Medium:   'bg-orange-400 text-white',
    Low:      'bg-blue-500 text-white',
  };

  const classes = colorMap[severity] ?? 'bg-gray-200 text-gray-800';

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-sm font-semibold ${classes}`}>
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const variantMap: Record<string, 'success' | 'warning' | 'danger' | 'info' | 'default'> = {
    draft: 'default',
    in_progress: 'info',
    completed: 'success',
    archived: 'default',
    open: 'warning',
    accepted: 'success',
    mitigating: 'info',
    closed: 'default',
    done: 'success',
  };

  const labelMap: Record<string, string> = {
    in_progress: 'In Progress',
    done: 'Done',
  };

  const label = labelMap[status] || status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <Badge variant={variantMap[status] || 'default'}>
      {label}
    </Badge>
  );
}
