'use client';

import { useState, useEffect } from 'react';
import { Search, Shield, RefreshCw, Globe, ChevronDown, ChevronRight, Zap, Database, Clock, AlertTriangle } from 'lucide-react';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';
import apiClient from '../lib/api-client';
import type { AttackGroup, ThreatEnrichmentsResponse, EnrichmentSummary } from '../lib/types';

interface IntelEnrichmentPanelProps {
  assessmentId: string;
  threatIds?: string[];
  onEnrichComplete?: () => void;
}

export function IntelEnrichmentPanel({ assessmentId, threatIds, onEnrichComplete }: IntelEnrichmentPanelProps) {
  const [enriching, setEnriching] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [groups, setGroups] = useState<AttackGroup[]>([]);
  const [groupSearch, setGroupSearch] = useState('');
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [showGroups, setShowGroups] = useState(false);

  const handleEnrich = async () => {
    try {
      setEnriching(true);
      setError(null);
      const res = await apiClient.enrichThreats({
        assessment_id: assessmentId,
        threat_ids: threatIds,
        force_refresh: false,
      });
      setResult(res);
      onEnrichComplete?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Enrichment failed');
    } finally {
      setEnriching(false);
    }
  };

  const loadGroups = async (search?: string) => {
    try {
      setLoadingGroups(true);
      const res = await apiClient.getAttackGroups({ search, limit: 20 });
      setGroups(res.groups);
    } catch {
      // Groups may not be seeded yet
      setGroups([]);
    } finally {
      setLoadingGroups(false);
    }
  };

  useEffect(() => {
    if (showGroups) {
      loadGroups(groupSearch || undefined);
    }
  }, [showGroups, groupSearch]);

  return (
    <div className="bg-card rounded-lg border border-border p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <Database className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Threat Intelligence Enrichment</h3>
            <p className="text-sm text-muted-foreground">Dual-track enrichment: CVE-based + ATT&CK sector frequency</p>
          </div>
        </div>
        <Button onClick={handleEnrich} disabled={enriching} size="sm">
          {enriching ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Enriching...
            </>
          ) : (
            <>
              <Zap className="w-4 h-4 mr-2" />
              Enrich Threats
            </>
          )}
        </Button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 rounded-lg text-sm text-red-700 dark:text-red-400 mb-4">
          {error}
        </div>
      )}

      {result && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/40 rounded-lg mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-green-600 dark:text-green-400" />
            <span className="text-sm font-semibold text-green-800 dark:text-green-300">Enrichment Complete</span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-green-600 dark:text-green-400">Threats Enriched:</span>
              <span className="ml-2 font-bold text-green-800 dark:text-green-300">{result.threats_enriched}</span>
            </div>
            <div>
              <span className="text-green-600 dark:text-green-400">Status:</span>
              <span className="ml-2 font-bold text-green-800 dark:text-green-300">{result.status}</span>
            </div>
          </div>
        </div>
      )}

      {/* ATT&CK Groups Browser */}
      <div className="border-t border-border pt-4">
        <button
          onClick={() => setShowGroups(!showGroups)}
          className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary"
        >
          {showGroups ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <Globe className="w-4 h-4 text-purple-500" />
          ATT&CK Threat Groups
        </button>

        {showGroups && (
          <div className="mt-3">
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search groups..."
                value={groupSearch}
                onChange={(e) => setGroupSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            {loadingGroups ? (
              <div className="flex justify-center py-4"><LoadingSpinner /></div>
            ) : groups.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No threat groups found. Groups need to be synced from MITRE ATT&CK.
              </p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {groups.map((g) => (
                  <div key={g.id} className="p-3 bg-muted rounded-lg border border-border">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-sm font-semibold text-foreground">{g.name}</span>
                        {g.aliases.length > 0 && (
                          <span className="ml-2 text-xs text-muted-foreground">
                            aka {g.aliases.slice(0, 3).join(', ')}
                          </span>
                        )}
                      </div>
                      <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-2 py-0.5 rounded-full">
                        {g.technique_count} techniques
                      </span>
                    </div>
                    {g.description && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{g.description}</p>
                    )}
                    {g.target_sectors.length > 0 && (
                      <div className="flex gap-1 mt-2 flex-wrap">
                        {g.target_sectors.slice(0, 5).map((s) => (
                          <span key={s} className="text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 px-1.5 py-0.5 rounded">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Small badge for showing enrichment status on a threat card
export function EnrichmentBadge({ threatId }: { threatId: string }) {
  const [summary, setSummary] = useState<EnrichmentSummary | null>(null);

  useEffect(() => {
    apiClient.getThreatEnrichmentSummary(threatId).then(setSummary).catch(() => {});
  }, [threatId]);

  if (!summary || summary.total_sources === 0) return null;

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800/40">
      <Database className="w-3 h-3" />
      {summary.total_sources} intel source{summary.total_sources !== 1 ? 's' : ''}
    </span>
  );
}
