'use client';

import { useEffect, useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { SkeletonTable } from '../../components/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { Badge } from '../../components/Badge';
import { EmptyState } from '../../components/EmptyState';
import { Breadcrumb } from '../../components/Breadcrumb';
import apiClient from '../../lib/api-client';
import { AuditLog } from '../../lib/types';
import { format } from 'date-fns';

export default function AuditLogsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [filter, setFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const [entityTypeFilter, setEntityTypeFilter] = useState('all');

  useEffect(() => {
    loadLogs();
  }, [actionFilter, entityTypeFilter]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = { limit: 100 };
      if (actionFilter !== 'all') {
        params.action = actionFilter;
      }
      if (entityTypeFilter !== 'all') {
        params.resource_type = entityTypeFilter;
      }
      const items = await apiClient.getAuditLogs(params);
      setLogs(items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter((log) =>
    log.resource_type.toLowerCase().includes(filter.toLowerCase()) ||
    log.resource_id.toLowerCase().includes(filter.toLowerCase())
  );

  const getActionBadgeVariant = (action: string): 'success' | 'warning' | 'danger' | 'info' => {
    switch (action) {
      case 'CREATE':
        return 'success';
      case 'UPDATE':
        return 'info';
      case 'DELETE':
        return 'danger';
      default:
        return 'warning';
    }
  };

  const inputClass = "bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors";

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="skeleton h-8 w-40 rounded" />
        <SkeletonTable rows={8} />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <Breadcrumb items={[{ label: 'Audit Logs' }]} />

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Audit Logs</h1>
        <p className="text-muted-foreground mt-1">Complete audit trail of all system changes</p>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Filters */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by entity type or ID..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className={`w-full pl-9 pr-4 py-2 ${inputClass}`}
            />
          </div>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className={`px-4 py-2 ${inputClass}`}
          >
            <option value="all">All Actions</option>
            <option value="CREATE">Create</option>
            <option value="UPDATE">Update</option>
            <option value="DELETE">Delete</option>
          </select>
          <select
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
            className={`px-4 py-2 ${inputClass}`}
          >
            <option value="all">All Entity Types</option>
            <option value="Assessment">Assessment</option>
            <option value="Threat">Threat</option>
            <option value="Evidence">Evidence</option>
            <option value="Recommendation">Recommendation</option>
            <option value="ActiveRisk">Active Risk</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      {filteredLogs.length === 0 ? (
        <div className="bg-card rounded-xl border border-border">
          <EmptyState
            icon={filter ? 'search' : 'audit'}
            title={filter ? 'No matching logs' : 'No audit logs yet'}
            description={filter ? 'Try adjusting your search or filters' : 'Activity will appear here as changes are made'}
          />
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden shadow-sm">
          <table className="min-w-full divide-y divide-border">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Entity Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Entity ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Changes
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                    {format(new Date(log.created_at), 'MMM d, yyyy HH:mm:ss')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant={getActionBadgeVariant(log.action_type)} size="sm">
                      {log.action_type}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                    {log.resource_type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-muted-foreground">
                    {log.resource_id.substring(0, 8)}...
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                    {log.actor_user_id?.substring(0, 8) || 'System'}
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {log.changes && (
                      <details className="cursor-pointer">
                        <summary className="text-primary hover:underline">
                          View changes
                        </summary>
                        <div className="mt-2 p-2 bg-muted rounded-lg text-xs font-mono max-w-md overflow-auto text-foreground">
                          <pre>{JSON.stringify(log.changes, null, 2)}</pre>
                        </div>
                      </details>
                    )}
                    {log.action_type === 'DELETE' && (
                      <span className="text-red-600 dark:text-red-400">Record deleted</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
