'use client';

import { useEffect, useState, useCallback } from 'react';
import { Shield, Zap, Plus, Loader2, ChevronDown, ChevronUp, ExternalLink, Bot } from 'lucide-react';
import apiClient from '../lib/api-client';
import { ThreatAttackMapping, KillChain } from '../lib/types';
import { TacticMatrix } from './TacticMatrix';
import { KillChainFlow } from './KillChainFlow';
import { AttackMappingModal } from './AttackMappingModal';

interface AttackContextPanelProps {
  threatId: string;
  threatTitle: string;
}

function ConfidenceBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-green-100 text-green-700' :
    score >= 60 ? 'bg-yellow-100 text-yellow-700' :
    'bg-red-100 text-red-700';
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-mono font-medium ${color}`}>
      {score}%
    </span>
  );
}

export function AttackContextPanel({ threatId, threatTitle }: AttackContextPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [mappings, setMappings] = useState<ThreatAttackMapping[]>([]);
  const [killChains, setKillChains] = useState<KillChain[]>([]);
  const [loadingMappings, setLoadingMappings] = useState(false);
  const [loadingKillChains, setLoadingKillChains] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showMappingModal, setShowMappingModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dataLoaded, setDataLoaded] = useState(false);

  const loadData = useCallback(async () => {
    if (dataLoaded) return;
    setLoadingMappings(true);
    setLoadingKillChains(true);
    setError(null);
    try {
      const [mappingsData, killChainsData] = await Promise.all([
        apiClient.getThreatMappings(threatId),
        apiClient.getKillChains(threatId),
      ]);
      setMappings(mappingsData);
      setKillChains(killChainsData);
      setDataLoaded(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load ATT&CK data');
    } finally {
      setLoadingMappings(false);
      setLoadingKillChains(false);
    }
  }, [threatId, dataLoaded]);

  // Load data when panel is expanded
  useEffect(() => {
    if (expanded && !dataLoaded) {
      loadData();
    }
  }, [expanded, dataLoaded, loadData]);

  const handleMappingsChanged = useCallback(async () => {
    setLoadingMappings(true);
    try {
      const data = await apiClient.getThreatMappings(threatId);
      setMappings(data);
    } catch (_) {
    } finally {
      setLoadingMappings(false);
    }
  }, [threatId]);

  const handleGenerateKillChain = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setGenerating(true);
    setError(null);
    try {
      const kc = await apiClient.generateKillChain(threatId, {});
      setKillChains((prev) => [kc, ...prev]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate kill chain scenario');
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteKillChain = useCallback(async (killChainId: string) => {
    try {
      await apiClient.deleteKillChain(killChainId);
      setKillChains((prev) => prev.filter((kc) => kc.id !== killChainId));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete kill chain');
    }
  }, []);

  const mappedTacticIds = Array.from(new Set(mappings.map((m) => m.technique?.tactic_id).filter(Boolean))) as string[];

  return (
    <div
      className="mt-3 border-t border-gray-100 pt-3"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Collapsible header */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setExpanded((v) => !v);
        }}
        className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-muted transition-colors group"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-orange-500" />
          <span className="text-sm font-semibold text-foreground">ATT&CK Context</span>
          {mappings.length > 0 && (
            <span className="text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 px-1.5 py-0.5 rounded-full font-medium">
              {mappings.length} technique{mappings.length !== 1 ? 's' : ''}
            </span>
          )}
          {killChains.length > 0 && (
            <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-1.5 py-0.5 rounded-full font-medium">
              {killChains.length} kill chain{killChains.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-3 space-y-4">
          {error && (
            <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}

          {/* Tactic Matrix */}
          <TacticMatrix mappings={mappings} />

          {/* Mapped Techniques chips */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Mapped Techniques
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMappingModal(true);
                }}
                className="inline-flex items-center gap-1 text-xs font-medium text-orange-600 hover:text-orange-800 hover:bg-orange-50 px-2 py-1 rounded-lg transition-colors"
              >
                <Plus className="w-3 h-3" />
                Manage Mappings
              </button>
            </div>

            {loadingMappings ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                Loading...
              </div>
            ) : mappings.length === 0 ? (
              <p className="text-xs text-muted-foreground italic py-1">
                No techniques mapped yet. Click "Manage Mappings" to add or auto-suggest.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {mappings.map((mapping) => (
                  <div
                    key={mapping.id}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800/40 rounded-lg text-xs"
                    title={mapping.technique?.name || mapping.technique_id}
                  >
                    <a
                      href={`https://attack.mitre.org/techniques/${mapping.technique?.mitre_id?.replace('.', '/')}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="font-mono font-bold text-orange-700 dark:text-orange-400 hover:text-orange-900 dark:hover:text-orange-300 hover:underline"
                    >
                      {mapping.technique?.mitre_id || '—'}
                    </a>
                    <span className="text-muted-foreground max-w-[140px] truncate">
                      {mapping.technique?.name || mapping.technique_id}
                    </span>
                    <ConfidenceBadge score={mapping.confidence_score} />
                    {mapping.auto_mapped && (
                      <span title="AI suggested">
                        <Bot className="w-3 h-3 text-indigo-400" />
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Kill Chains section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Attack Scenarios
              </span>
              <button
                onClick={handleGenerateKillChain}
                disabled={generating}
                className="inline-flex items-center gap-1 text-xs font-medium text-purple-600 hover:text-purple-800 hover:bg-purple-50 px-2 py-1 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Building...
                  </>
                ) : (
                  <>
                    <Zap className="w-3 h-3" />
                    Build Threat Progression
                  </>
                )}
              </button>
            </div>

            {loadingKillChains ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                Loading...
              </div>
            ) : killChains.length === 0 ? (
              <p className="text-xs text-muted-foreground italic py-1">
                No threat progressions built yet. Map ATT&amp;CK techniques first, then click
                &ldquo;Build Threat Progression&rdquo; to generate a validated ATT&amp;CK kill chain.
              </p>
            ) : (
              <div className="space-y-3">
                {killChains.map((kc) => (
                  <KillChainFlow
                    key={kc.id}
                    killChain={kc}
                    onDelete={handleDeleteKillChain}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Mapping Modal */}
      {showMappingModal && (
        <AttackMappingModal
          threatId={threatId}
          threatTitle={threatTitle}
          onClose={() => setShowMappingModal(false)}
          onMappingsChanged={handleMappingsChanged}
        />
      )}
    </div>
  );
}
