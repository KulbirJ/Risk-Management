'use client';

/**
 * TacticMatrix – visualises MITRE ATT&CK tactics as a heatmap-style grid.
 *
 * Each tactic column shows the technique count and, when mapped techniques are
 * passed in, highlights cells that have been mapped for the current threat.
 */

import { useEffect, useState } from 'react';
import { Shield, RefreshCw, ExternalLink, AlertCircle } from 'lucide-react';
import apiClient from '../lib/api-client';
import type { AttackTactic, ThreatAttackMapping, AttackSyncStatus } from '../lib/types';

interface TacticMatrixProps {
  /** Threat-level mappings to highlight relevant tactics */
  mappings?: ThreatAttackMapping[];
  /** Called when tactic cell is clicked */
  onTacticClick?: (tactic: AttackTactic) => void;
}

export function TacticMatrix({ mappings = [], onTacticClick }: TacticMatrixProps) {
  const [tactics, setTactics] = useState<AttackTactic[]>([]);
  const [syncStatus, setSyncStatus] = useState<AttackSyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Build a set of tactic shortnames that appear in the current mappings
  const mappedTactics = new Set(
    mappings.map((m) => m.technique?.tactic_shortname).filter(Boolean),
  );

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [tacticList, status] = await Promise.all([
        apiClient.getAttackTactics(),
        apiClient.getAttackSyncStatus(),
      ]);
      setTactics(tacticList);
      setSyncStatus(status);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load ATT&CK tactics');
    } finally {
      setLoading(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setError(null);
    try {
      const status = await apiClient.triggerAttackSync();
      setSyncStatus(status);
      await loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Sync failed – check server logs');
    } finally {
      setSyncing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-400">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
        Loading ATT&amp;CK tactics…
      </div>
    );
  }

  if (syncStatus?.sync_status === 'never' || tactics.length === 0) {
    return (
      <div className="border border-dashed border-gray-600 rounded-lg p-6 text-center">
        <Shield className="w-10 h-10 mx-auto mb-3 text-gray-500" />
        <p className="text-gray-300 font-medium mb-1">ATT&amp;CK data not yet loaded</p>
        <p className="text-gray-500 text-sm mb-4">
          Sync the MITRE ATT&amp;CK framework to see tactic coverage.
        </p>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
        >
          {syncing ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          {syncing ? 'Syncing ATT&CK data…' : 'Sync Now'}
        </button>
        {error && (
          <p className="text-red-400 text-sm mt-3 flex items-center justify-center gap-1">
            <AlertCircle className="w-4 h-4" />
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Shield className="w-4 h-4 text-blue-400" />
          <span>
            {syncStatus?.tactics_count ?? tactics.length} tactics ·{' '}
            {syncStatus?.techniques_count ?? '?'} techniques
          </span>
          {syncStatus?.last_synced_at && (
            <span className="text-gray-600">
              · synced {new Date(syncStatus.last_synced_at).toLocaleDateString()}
            </span>
          )}
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${syncing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Tactic grid */}
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        {tactics.map((tactic) => {
          const isHighlighted = mappedTactics.has(tactic.shortname);
          return (
            <button
              key={tactic.id}
              onClick={() => onTacticClick?.(tactic)}
              title={tactic.description || tactic.name}
              className={`
                relative flex flex-col items-center justify-center p-2 rounded-lg text-center
                transition-all border cursor-pointer
                ${
                  isHighlighted
                    ? 'bg-orange-900/40 border-orange-500 shadow-orange-900/50 shadow-sm'
                    : 'bg-gray-800/60 border-gray-700 hover:border-gray-500 hover:bg-gray-800'
                }
              `}
            >
              {isHighlighted && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-orange-400" />
              )}
              <p className={`text-xs font-semibold leading-tight ${isHighlighted ? 'text-orange-200' : 'text-gray-200'}`}>
                {tactic.name}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{tactic.mitre_id}</p>
              {(tactic.technique_count ?? 0) > 0 && (
                <span className={`text-xs mt-1 ${isHighlighted ? 'text-orange-400' : 'text-gray-600'}`}>
                  {tactic.technique_count} techniques
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-orange-900/40 border border-orange-500 inline-block" />
          Mapped for this threat
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-gray-800/60 border border-gray-700 inline-block" />
          Not mapped
        </span>
      </div>

      {error && (
        <p className="text-red-400 text-sm flex items-center gap-1">
          <AlertCircle className="w-4 h-4" />
          {error}
        </p>
      )}
    </div>
  );
}
