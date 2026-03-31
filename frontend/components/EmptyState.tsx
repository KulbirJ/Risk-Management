'use client';

import { ReactNode } from 'react';
import { FileText, Shield, AlertTriangle, History, Search, Plus, FolderOpen } from 'lucide-react';
import { Button } from './Button';

type EmptyStateIcon = 'assessments' | 'risks' | 'threats' | 'audit' | 'search' | 'generic';

interface EmptyStateProps {
  icon?: EmptyStateIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  children?: ReactNode;
}

const iconMap: Record<EmptyStateIcon, typeof FileText> = {
  assessments: FileText,
  risks: AlertTriangle,
  threats: Shield,
  audit: History,
  search: Search,
  generic: FolderOpen,
};

const iconColorMap: Record<EmptyStateIcon, string> = {
  assessments: 'text-blue-400 dark:text-blue-500',
  risks: 'text-amber-400 dark:text-amber-500',
  threats: 'text-red-400 dark:text-red-500',
  audit: 'text-purple-400 dark:text-purple-500',
  search: 'text-gray-400 dark:text-gray-500',
  generic: 'text-gray-400 dark:text-gray-500',
};

const iconBgMap: Record<EmptyStateIcon, string> = {
  assessments: 'bg-blue-50 dark:bg-blue-900/20',
  risks: 'bg-amber-50 dark:bg-amber-900/20',
  threats: 'bg-red-50 dark:bg-red-900/20',
  audit: 'bg-purple-50 dark:bg-purple-900/20',
  search: 'bg-gray-50 dark:bg-gray-800',
  generic: 'bg-gray-50 dark:bg-gray-800',
};

export function EmptyState({
  icon = 'generic',
  title,
  description,
  actionLabel,
  onAction,
  children,
}: EmptyStateProps) {
  const Icon = iconMap[icon];

  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center animate-fade-in">
      <div className={`rounded-2xl p-5 mb-5 ${iconBgMap[icon]}`}>
        <Icon className={`w-10 h-10 ${iconColorMap[icon]}`} strokeWidth={1.5} />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <Button onClick={onAction}>
          <Plus className="w-4 h-4 mr-2" />
          {actionLabel}
        </Button>
      )}
      {children}
    </div>
  );
}
