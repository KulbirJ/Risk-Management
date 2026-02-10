'use client';

import { useEffect, useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { LoadingPage } from '../../components/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { Badge } from '../../components/Badge';
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

  if (loading) {
    return <LoadingPage />;
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-gray-600 mt-1">Complete audit trail of all system changes</p>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by entity type or ID..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">All Actions</option>
            <option value="CREATE">Create</option>
            <option value="UPDATE">Update</option>
            <option value="DELETE">Delete</option>
          </select>
          <select
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
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
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No audit logs found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entity Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entity ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Changes
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {format(new Date(log.created_at), 'MMM d, yyyy HH:mm:ss')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant={getActionBadgeVariant(log.action_type)} size="sm">
                      {log.action_type}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {log.resource_type}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                    {log.resource_id.substring(0, 8)}...
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {log.actor_user_id?.substring(0, 8) || 'System'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {log.changes && (
                      <details className="cursor-pointer">
                        <summary className="text-blue-600 hover:underline">
                          View changes
                        </summary>
                        <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono max-w-md overflow-auto">
                          <pre>{JSON.stringify(log.changes, null, 2)}</pre>
                        </div>
                      </details>
                    )}
                    {log.action_type === 'DELETE' && (
                      <span className="text-red-600">Record deleted</span>
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
