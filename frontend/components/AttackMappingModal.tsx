'use client';

/**
 * AttackMappingModal – Manage ATT&CK technique mappings for a threat.
 *
 * Features:
 *  - Tabs: "AI Suggestions" (auto-map) and "Search" (manual add)
 *  - Shows existing mappings with confidence badges
 *  - AI suggestions can be individually accepted or rejected
 *  - Manual technique search with instant add
 */

import { useState, useEffect, useRef } from 'react';
import {
  X,
  Zap,
  Search,
  CheckCircle,
  XCircle,
  Loader2,
  Brain,
  ExternalLink,
  Trash2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import apiClient from '../lib/api-client';
import type {
  ThreatAttackMapping,
  AutoMapSuggestion,
  AttackTechniqueSummary,
} from '../lib/types';

// ─── helpers ──────────────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-green-900/50 text-green-300 border-green-700' :
    score >= 60 ? 'bg-yellow-900/50 text-yellow-300 border-yellow-700' :
                  'bg-red-900/50 text-red-300 border-red-700';
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded border ${color}`}>
      {score}%
    </span>
  );
}

// ─── main component ──────────────────────────────────────────────

interface AttackMappingModalProps {
  threatId: string;
  threatTitle: string;
  onClose: () => void;
  onMappingsChanged?: () => void;
}

type Tab = 'mappings' | 'ai' | 'search';

export function AttackMappingModal({
  threatId,
  threatTitle,
  onClose,
  onMappingsChanged,
}: AttackMappingModalProps) {
  const [tab, setTab] = useState<Tab>('mappings');

  // Existing mappings
  const [mappings, setMappings] = useState<ThreatAttackMapping[]>([]);
  const [loadingMappings, setLoadingMappings] = useState(true);
  const [removingId, setRemovingId] = useState<string | null>(null);

  // AI suggestions tab
  const [autoMapping, setAutoMapping] = useState(false);
  const [suggestions, setSuggestions] = useState<AutoMapSuggestion[]>([]);
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set());
  const [rejectedIds, setRejectedIds] = useState<Set<string>>(new Set());
  const [aiError, setAiError] = useState<string | null>(null);
  const [savedCount, setSavedCount] = useState<number | null>(null);

  // Search tab
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<AttackTechniqueSummary[]>([]);
  const [searching, setSearching] = useState(false);
  const [addingId, setAddingId] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [error, setError] = useState<string | null>(null);

  // ── load existing mappings ────────────────────────────────────

  useEffect(() => {
    loadMappings();
  }, [threatId]);

  async function loadMappings() {
    setLoadingMappings(true);
    try {
      const data = await apiClient.getThreatMappings(threatId);
      setMappings(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load mappings');
    } finally {
      setLoadingMappings(false);
    }
  }

  // ── remove mapping ────────────────────────────────────────────

  async function handleRemove(techniqueId: string) {
    setRemovingId(techniqueId);
    try {
      await apiClient.removeThreatMapping(threatId, techniqueId);
      setMappings((prev) => prev.filter((m) => m.technique_id !== techniqueId));
      onMappingsChanged?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Remove failed');
    } finally {
      setRemovingId(null);
    }
  }

  // ── AI auto-map ───────────────────────────────────────────────

  async function handleAutoMap() {
    setAutoMapping(true);
    setAiError(null);
    setSuggestions([]);
    setSavedCount(null);
    setAcceptedIds(new Set());
    setRejectedIds(new Set());
    try {
      const result = await apiClient.autoMapThreat(threatId, {
        save_suggestions: true,
        confidence_threshold: 60,
      });
      setSuggestions(result.suggestions);
      setSavedCount(result.saved_count);
      if (result.saved_count > 0) {
        await loadMappings();
        onMappingsChanged?.();
      }
    } catch (err: any) {
      setAiError(err?.response?.data?.detail || 'AI mapping failed');
    } finally {
      setAutoMapping(false);
    }
  }

  async function acceptSuggestion(s: AutoMapSuggestion) {
    if (!s.technique_id) return;
    try {
      await apiClient.addThreatMapping(
        threatId,
        s.technique_id,
        s.confidence_score,
        s.mapping_rationale,
      );
      setAcceptedIds((prev) => new Set([...prev, s.mitre_id]));
      await loadMappings();
      onMappingsChanged?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to accept suggestion');
    }
  }

  // ── search ────────────────────────────────────────────────────

  useEffect(() => {
    if (tab !== 'search') return;
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await apiClient.searchAttackTechniques(searchQuery, 20);
        setSearchResults(results);
      } catch {
        // silently ignore
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => {
      if (searchTimer.current) clearTimeout(searchTimer.current);
    };
  }, [searchQuery, tab]);

  const mappedTechniqueIds = new Set(mappings.map((m) => m.technique_id));

  async function handleAddTechnique(t: AttackTechniqueSummary) {
    setAddingId(t.id);
    try {
      await apiClient.addThreatMapping(threatId, t.id, 80);
      await loadMappings();
      onMappingsChanged?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to add mapping');
    } finally {
      setAddingId(null);
    }
  }

  // ─────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-800">
          <div>
            <h2 className="text-base font-bold text-white">ATT&amp;CK Technique Mappings</h2>
            <p className="text-sm text-gray-400 mt-0.5 truncate max-w-xs">{threatTitle}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800 px-5">
          {(['mappings', 'ai', 'search'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-2.5 px-4 text-sm font-medium border-b-2 transition-colors capitalize ${
                tab === t
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              {t === 'ai' ? 'AI Suggestions' : t === 'search' ? 'Search & Add' : 'Current Mappings'}
              {t === 'mappings' && mappings.length > 0 && (
                <span className="ml-1.5 text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded-full">
                  {mappings.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* ── Mappings tab ── */}
          {tab === 'mappings' && (
            <>
              {loadingMappings ? (
                <div className="flex items-center justify-center py-8 text-gray-500">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Loading…
                </div>
              ) : mappings.length === 0 ? (
                <div className="text-center py-8">
                  <Brain className="w-10 h-10 mx-auto text-gray-600 mb-3" />
                  <p className="text-gray-400">No techniques mapped yet.</p>
                  <p className="text-gray-600 text-sm mt-1">
                    Use the &ldquo;AI Suggestions&rdquo; or &ldquo;Search &amp; Add&rdquo; tabs.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {mappings.map((m) => (
                    <div
                      key={m.id}
                      className="flex items-center gap-3 bg-gray-800/60 border border-gray-700 rounded-lg p-3"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-mono text-blue-400">
                            {m.technique.mitre_id}
                          </span>
                          <span className="text-sm font-medium text-white truncate">
                            {m.technique.name}
                          </span>
                          {m.auto_mapped && (
                            <span className="text-xs bg-purple-900/40 border border-purple-800 text-purple-400 px-1.5 py-0.5 rounded">
                              AI
                            </span>
                          )}
                        </div>
                        {m.technique.tactic_shortname && (
                          <p className="text-xs text-gray-500 mt-0.5">{m.technique.tactic_shortname}</p>
                        )}
                        {m.mapping_rationale && (
                          <p className="text-xs text-gray-500 mt-0.5 truncate">{m.mapping_rationale}</p>
                        )}
                      </div>
                      <ConfidenceBadge score={m.confidence_score} />
                      <a
                        href={`https://attack.mitre.org/techniques/${m.technique.mitre_id.replace('.', '/')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-600 hover:text-blue-400 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                      <button
                        onClick={() => handleRemove(m.technique_id)}
                        disabled={removingId === m.technique_id}
                        className="text-gray-600 hover:text-red-400 disabled:opacity-40 transition-colors"
                      >
                        {removingId === m.technique_id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* ── AI Suggestions tab ── */}
          {tab === 'ai' && (
            <div className="space-y-4">
              <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-4">
                <p className="text-sm text-blue-300 font-medium flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  AI-powered technique mapping
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Bedrock analyses the threat and picks the most relevant ATT&amp;CK techniques.
                  Suggestions above 60% confidence are auto-saved.
                </p>
                <button
                  onClick={handleAutoMap}
                  disabled={autoMapping}
                  className="mt-3 inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
                >
                  {autoMapping ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Zap className="w-4 h-4" />
                  )}
                  {autoMapping ? 'Analysing…' : 'Run AI Mapping'}
                </button>
              </div>

              {aiError && (
                <div className="text-red-400 text-sm flex items-center gap-2 bg-red-900/20 border border-red-800 rounded-lg p-3">
                  <AlertCircle className="w-4 h-4" />
                  {aiError}
                </div>
              )}

              {savedCount !== null && (
                <div className="text-green-400 text-sm flex items-center gap-2 bg-green-900/20 border border-green-800 rounded-lg p-3">
                  <CheckCircle className="w-4 h-4" />
                  {savedCount > 0
                    ? `${savedCount} suggestion${savedCount !== 1 ? 's' : ''} saved automatically.`
                    : 'No high-confidence suggestions found.'}
                </div>
              )}

              {suggestions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                    {suggestions.length} suggestions
                  </p>
                  {suggestions.map((s) => {
                    const alreadyMapped = mappings.some(
                      (m) => m.technique?.mitre_id === s.mitre_id,
                    );
                    const isAccepted = acceptedIds.has(s.mitre_id);
                    const isRejected = rejectedIds.has(s.mitre_id);

                    return (
                      <div
                        key={s.mitre_id}
                        className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                          alreadyMapped || isAccepted
                            ? 'bg-green-900/20 border-green-800'
                            : isRejected
                            ? 'bg-gray-800/30 border-gray-700 opacity-50'
                            : 'bg-gray-800/60 border-gray-700'
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono text-blue-400">{s.mitre_id}</span>
                            <span className="text-sm font-medium text-white">{s.technique_name}</span>
                            {s.tactic_shortname && (
                              <span className="text-xs text-gray-500">{s.tactic_shortname}</span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mt-1 leading-snug">{s.mapping_rationale}</p>
                        </div>
                        <ConfidenceBadge score={s.confidence_score} />
                        {alreadyMapped || isAccepted ? (
                          <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                        ) : isRejected ? (
                          <XCircle className="w-5 h-5 text-gray-600 flex-shrink-0" />
                        ) : (
                          <div className="flex gap-1 flex-shrink-0">
                            <button
                              onClick={() => acceptSuggestion(s)}
                              className="text-green-400 hover:text-green-300 transition-colors"
                              title="Accept"
                            >
                              <CheckCircle className="w-5 h-5" />
                            </button>
                            <button
                              onClick={() => setRejectedIds((p) => new Set([...p, s.mitre_id]))}
                              className="text-gray-600 hover:text-red-400 transition-colors"
                              title="Reject"
                            >
                              <XCircle className="w-5 h-5" />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ── Search tab ── */}
          {tab === 'search' && (
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search techniques by name or ID…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  autoFocus
                />
                {searching && (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 animate-spin" />
                )}
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-1.5">
                  {searchResults.map((t) => {
                    const alreadyMapped = mappedTechniqueIds.has(t.id);
                    return (
                      <div
                        key={t.id}
                        className="flex items-center gap-3 bg-gray-800/60 border border-gray-700 rounded-lg px-3 py-2.5"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-blue-400 flex-shrink-0">
                              {t.mitre_id}
                            </span>
                            <span className="text-sm text-white truncate">{t.name}</span>
                            {t.is_subtechnique && (
                              <span className="text-xs text-gray-600 flex-shrink-0">sub</span>
                            )}
                          </div>
                          {t.tactic_shortname && (
                            <p className="text-xs text-gray-500 mt-0.5">{t.tactic_shortname}</p>
                          )}
                        </div>
                        {alreadyMapped ? (
                          <span className="text-xs text-green-400 flex items-center gap-1 flex-shrink-0">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Mapped
                          </span>
                        ) : (
                          <button
                            onClick={() => handleAddTechnique(t)}
                            disabled={addingId === t.id}
                            className="text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white px-3 py-1 rounded-md transition-colors flex-shrink-0"
                          >
                            {addingId === t.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              'Add'
                            )}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {searchQuery.length >= 2 && !searching && searchResults.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">
                  No techniques found for &ldquo;{searchQuery}&rdquo;
                </p>
              )}

              {!searchQuery && (
                <p className="text-gray-600 text-sm text-center py-4">
                  Type at least 2 characters to search ATT&amp;CK techniques.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800 flex justify-end">
          <button
            onClick={onClose}
            className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-5 py-2 rounded-lg transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
