'use client';

/**
 * AttackMappingModal â€“ Manage ATT&CK technique mappings for a threat.
 *
 * Tabs:
 *  1. Current Mappings  â€“ list + remove existing mappings
 *  2. Browse Matrix     â€“ ATT&CK Navigator-style grid; click cells to add/remove
 *  3. AI Suggestions    â€“ Bedrock auto-map
 *  4. Search & Add      â€“ text search
 */

import { useState, useEffect, useRef, useMemo } from 'react';
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
  LayoutGrid,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import apiClient from '../lib/api-client';
import type {
  ThreatAttackMapping,
  AutoMapSuggestion,
  AttackTechniqueSummary,
  AttackTactic,
  AttackTechnique,
} from '../lib/types';

// â”€â”€â”€ tactic colour palette (matches KillChainFlow) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const TACTIC_COLORS: Record<string, { bg: string; border: string; header: string; text: string }> = {
  'reconnaissance':       { bg: '#1e293b', border: '#0ea5e9', header: '#0c4a6e', text: '#38bdf8' },
  'resource-development': { bg: '#1e1b2e', border: '#a855f7', header: '#3b0764', text: '#c084fc' },
  'initial-access':       { bg: '#1a2e1a', border: '#22c55e', header: '#14532d', text: '#4ade80' },
  'execution':            { bg: '#2d1a1a', border: '#ef4444', header: '#7f1d1d', text: '#f87171' },
  'persistence':          { bg: '#2d1e0e', border: '#f97316', header: '#7c2d12', text: '#fb923c' },
  'privilege-escalation': { bg: '#2a1f0d', border: '#eab308', header: '#713f12', text: '#facc15' },
  'defense-evasion':      { bg: '#1a2535', border: '#3b82f6', header: '#1e3a5f', text: '#60a5fa' },
  'credential-access':    { bg: '#1e1a2e', border: '#8b5cf6', header: '#2e1065', text: '#a78bfa' },
  'discovery':            { bg: '#0f2329', border: '#06b6d4', header: '#164e63', text: '#22d3ee' },
  'lateral-movement':     { bg: '#0f271f', border: '#10b981', header: '#064e3b', text: '#34d399' },
  'collection':           { bg: '#241f0e', border: '#d97706', header: '#78350f', text: '#fbbf24' },
  'command-and-control':  { bg: '#0e2222', border: '#14b8a6', header: '#134e4a', text: '#2dd4bf' },
  'exfiltration':         { bg: '#2a1a2e', border: '#ec4899', header: '#831843', text: '#f472b6' },
  'impact':               { bg: '#2a1a1a', border: '#dc2626', header: '#7f1d1d', text: '#f87171' },
};

function tacticColor(shortname: string) {
  return TACTIC_COLORS[shortname] ?? { bg: '#1f2937', border: '#6b7280', header: '#374151', text: '#d1d5db' };
}

// â”€â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

// â”€â”€â”€ Matrix column â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface TacticColumnProps {
  tactic: AttackTactic;
  techniques: AttackTechnique[] | undefined;
  loading: boolean;
  mappedIds: Set<string>;
  togglingId: string | null;
  filter: string;
  onToggle: (tech: AttackTechnique) => void;
  onVisible: (tacticId: string) => void;
}

function TacticColumn({ tactic, techniques, loading, mappedIds, togglingId, filter, onToggle, onVisible }: TacticColumnProps) {
  const colRef = useRef<HTMLDivElement>(null);
  const [expandedParents, setExpandedParents] = useState<Set<string>>(new Set());
  const palette = tacticColor(tactic.shortname);

  // Report visibility so parent can lazily request technique load
  useEffect(() => {
    const el = colRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        onVisible(tactic.id);
        obs.disconnect();
      }
    }, { threshold: 0.01 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [tactic.id, onVisible]);

  // Group into parents + sub-techniques
  const parents = useMemo(() => {
    if (!techniques) return [];
    return techniques.filter(t => !t.is_subtechnique);
  }, [techniques]);

  const subsByParent = useMemo(() => {
    const m = new Map<string, AttackTechnique[]>();
    if (!techniques) return m;
    techniques.filter(t => t.is_subtechnique).forEach(sub => {
      // sub mitre_id is e.g. T1566.001; parent prefix is T1566
      const parentId = sub.mitre_id.split('.')[0];
      if (!m.has(parentId)) m.set(parentId, []);
      m.get(parentId)!.push(sub);
    });
    return m;
  }, [techniques]);

  const lowerFilter = filter.toLowerCase();

  function matchesFilter(t: AttackTechnique) {
    if (!lowerFilter) return true;
    return t.name.toLowerCase().includes(lowerFilter) || t.mitre_id.toLowerCase().includes(lowerFilter);
  }

  function parentMatchesOrHasMatchingSub(p: AttackTechnique) {
    if (matchesFilter(p)) return true;
    const subs = subsByParent.get(p.mitre_id) ?? [];
    return subs.some(matchesFilter);
  }

  const visibleParents = parents.filter(parentMatchesOrHasMatchingSub);

  const mappedCount = techniques ? techniques.filter(t => mappedIds.has(t.id)).length : 0;

  return (
    <div
      ref={colRef}
      className="flex-shrink-0 w-52 flex flex-col rounded-lg overflow-hidden border"
      style={{ borderColor: palette.border, background: palette.bg }}
    >
      {/* Column header */}
      <div
        className="px-2 py-2 text-center"
        style={{ background: palette.header }}
      >
        <p className="text-xs font-bold uppercase tracking-wide truncate" style={{ color: palette.text }}>
          {tactic.name}
        </p>
        <div className="flex items-center justify-center gap-2 mt-0.5">
          <span className="text-xs text-gray-400">{tactic.technique_count ?? 0} techniques</span>
          {mappedCount > 0 && (
            <span className="text-xs font-semibold px-1.5 py-0 rounded-full" style={{ background: palette.border, color: '#fff' }}>
              {mappedCount} mapped
            </span>
          )}
        </div>
      </div>

      {/* Techniques list */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5" style={{ maxHeight: 420 }}>
        {loading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
          </div>
        ) : visibleParents.length === 0 ? (
          <p className="text-gray-600 text-xs text-center py-4">No match</p>
        ) : (
          visibleParents.map(parent => {
            const isMapped = mappedIds.has(parent.id);
            const isToggling = togglingId === parent.id;
            const subs = subsByParent.get(parent.mitre_id) ?? [];
            const visibleSubs = lowerFilter ? subs.filter(matchesFilter) : subs;
            const isExpanded = expandedParents.has(parent.id);
            const hasSubs = subs.length > 0;

            return (
              <div key={parent.id}>
                {/* Parent technique cell */}
                <div
                  className={`group flex items-start gap-1 rounded px-1.5 py-1 cursor-pointer transition-all select-none ${
                    isMapped
                      ? 'border border-green-500/50'
                      : 'border border-transparent hover:border-gray-600'
                  }`}
                  style={{ background: isMapped ? 'rgba(34,197,94,0.12)' : 'rgba(255,255,255,0.03)' }}
                  onClick={() => onToggle(parent)}
                  title={parent.description ? parent.description.slice(0, 200) : parent.name}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <span className="text-xs font-mono flex-shrink-0" style={{ color: palette.text }}>
                        {parent.mitre_id}
                      </span>
                    </div>
                    <p className="text-xs text-gray-200 leading-tight mt-0.5 line-clamp-2">
                      {parent.name}
                    </p>
                  </div>
                  {/* Status icon */}
                  <div className="flex-shrink-0 mt-0.5 w-4">
                    {isToggling ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />
                    ) : isMapped ? (
                      <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-gray-600 group-hover:border-blue-400 transition-colors" />
                    )}
                  </div>
                </div>

                {/* Sub-techniques toggle */}
                {hasSubs && (visibleSubs.length > 0) && (
                  <div className="ml-2 mt-0.5">
                    {(!lowerFilter) && (
                      <button
                        className="flex items-center gap-0.5 text-xs text-gray-600 hover:text-gray-400 px-1 py-0.5 mb-0.5"
                        onClick={e => {
                          e.stopPropagation();
                          setExpandedParents(prev => {
                            const s = new Set(prev);
                            if (s.has(parent.id)) s.delete(parent.id);
                            else s.add(parent.id);
                            return s;
                          });
                        }}
                      >
                        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        {subs.length} sub-technique{subs.length !== 1 ? 's' : ''}
                      </button>
                    )}

                    {/* Sub-technique cells (shown when expanded or filter active) */}
                    {(isExpanded || !!lowerFilter) && visibleSubs.map(sub => {
                      const subMapped = mappedIds.has(sub.id);
                      const subToggling = togglingId === sub.id;
                      return (
                        <div
                          key={sub.id}
                          className={`group flex items-start gap-1 rounded px-1.5 py-1 cursor-pointer mb-0.5 transition-all select-none ${
                            subMapped ? 'border border-green-500/40' : 'border border-transparent hover:border-gray-700'
                          }`}
                          style={{ background: subMapped ? 'rgba(34,197,94,0.08)' : 'rgba(255,255,255,0.02)' }}
                          onClick={() => onToggle(sub)}
                          title={sub.name}
                        >
                          <div className="flex-1 min-w-0">
                            <span className="text-xs font-mono" style={{ color: palette.text, opacity: 0.8 }}>
                              {sub.mitre_id}
                            </span>
                            <p className="text-xs text-gray-400 leading-tight mt-0.5 line-clamp-2">
                              {sub.name}
                            </p>
                          </div>
                          <div className="flex-shrink-0 mt-0.5 w-4">
                            {subToggling ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />
                            ) : subMapped ? (
                              <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                            ) : (
                              <div className="w-3.5 h-3.5 rounded-full border border-gray-700 group-hover:border-blue-400 transition-colors" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// â”€â”€â”€ main component â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface AttackMappingModalProps {
  threatId: string;
  threatTitle: string;
  onClose: () => void;
  onMappingsChanged?: () => void;
}

type Tab = 'mappings' | 'matrix' | 'ai' | 'search';

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

  // Matrix tab
  const [matrixTactics, setMatrixTactics] = useState<AttackTactic[]>([]);
  const [techniquesByTactic, setTechniquesByTactic] = useState<Map<string, AttackTechnique[]>>(new Map());
  const [loadingTactics, setLoadingTactics] = useState(false);
  const [loadingTechIds, setLoadingTechIds] = useState<Set<string>>(new Set());
  const [matrixFilter, setMatrixFilter] = useState('');
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const loadedTacticIds = useRef<Set<string>>(new Set());

  const [error, setError] = useState<string | null>(null);

  // â”€â”€ load existing mappings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

  // â”€â”€ remove mapping â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

  // â”€â”€ AI auto-map â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

  // â”€â”€ search â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  useEffect(() => {
    if (tab !== 'search') return;
    if (!searchQuery.trim()) { setSearchResults([]); return; }
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await apiClient.searchAttackTechniques(searchQuery, 20);
        setSearchResults(results);
      } catch { /* ignore */ } finally {
        setSearching(false);
      }
    }, 350);
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current); };
  }, [searchQuery, tab]);

  // â”€â”€ matrix â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  useEffect(() => {
    if (tab !== 'matrix') return;
    if (matrixTactics.length > 0) return;
    loadMatrixTactics();
  }, [tab]);

  async function loadMatrixTactics() {
    setLoadingTactics(true);
    try {
      const tactics = await apiClient.getAttackTactics();
      const sorted = [...tactics].sort((a, b) => (a.phase_order ?? 99) - (b.phase_order ?? 99));
      setMatrixTactics(sorted);
    } finally {
      setLoadingTactics(false);
    }
  }

  function handleTacticVisible(tacticId: string) {
    if (loadedTacticIds.current.has(tacticId)) return;
    loadedTacticIds.current.add(tacticId);
    setLoadingTechIds(prev => new Set([...prev, tacticId]));
    apiClient.getTechniquesByTactic(tacticId, true).then(techs => {
      setTechniquesByTactic(prev => new Map([...prev, [tacticId, techs]]));
    }).finally(() => {
      setLoadingTechIds(prev => { const s = new Set(prev); s.delete(tacticId); return s; });
    });
  }

  async function handleToggleTechnique(tech: AttackTechnique) {
    const isMapped = mappedTechniqueIds.has(tech.id);
    setTogglingId(tech.id);
    try {
      if (isMapped) {
        await apiClient.removeThreatMapping(threatId, tech.id);
        setMappings(prev => prev.filter(m => m.technique_id !== tech.id));
      } else {
        const newMapping = await apiClient.addThreatMapping(threatId, tech.id, 80);
        setMappings(prev => [...prev, newMapping]);
      }
      onMappingsChanged?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Toggle failed');
    } finally {
      setTogglingId(null);
    }
  }

  // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

  const isMatrixTab = tab === 'matrix';

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className={`bg-gray-900 border border-gray-700 rounded-xl w-full max-h-[92vh] overflow-hidden flex flex-col shadow-2xl transition-all duration-200 ${
          isMatrixTab ? 'max-w-[92vw]' : 'max-w-2xl'
        }`}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-800 shrink-0">
          <div>
            <h2 className="text-base font-bold text-white">ATT&amp;CK Technique Mappings</h2>
            <p className="text-sm text-gray-400 mt-0.5 truncate max-w-xs">{threatTitle}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800 px-5 shrink-0 overflow-x-auto">
          {(['mappings', 'matrix', 'ai', 'search'] as Tab[]).map((t) => {
            const labels: Record<Tab, string> = {
              mappings: 'Current Mappings',
              matrix: 'Browse Matrix',
              ai: 'AI Suggest',
              search: 'Search & Add',
            };
            const icons: Record<Tab, React.ReactNode> = {
              mappings: null,
              matrix: <LayoutGrid className="w-3.5 h-3.5 mr-1" />,
              ai: <Zap className="w-3.5 h-3.5 mr-1" />,
              search: <Search className="w-3.5 h-3.5 mr-1" />,
            };
            return (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`py-2.5 px-4 text-sm font-medium border-b-2 transition-colors flex items-center whitespace-nowrap ${
                  tab === t
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                {icons[t]}
                {labels[t]}
                {t === 'mappings' && mappings.length > 0 && (
                  <span className="ml-1.5 text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded-full">
                    {mappings.length}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Body */}
        <div className={`flex-1 min-h-0 ${isMatrixTab ? 'flex flex-col' : 'overflow-y-auto p-5 space-y-4'}`}>
          {error && (
            <div className={`flex items-center gap-2 text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2 ${isMatrixTab ? 'mx-4 mt-3' : ''}`}>
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* â”€â”€ Current Mappings tab â”€â”€ */}
          {tab === 'mappings' && (
            <>
              {loadingMappings ? (
                <div className="flex items-center justify-center py-8 text-gray-500">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />Loadingâ€¦
                </div>
              ) : mappings.length === 0 ? (
                <div className="text-center py-8">
                  <Brain className="w-10 h-10 mx-auto text-gray-600 mb-3" />
                  <p className="text-gray-400">No techniques mapped yet.</p>
                  <p className="text-gray-600 text-sm mt-1">
                    Use the <strong className="text-gray-400">Browse Matrix</strong> tab to visually pick techniques,
                    or try <strong className="text-gray-400">AI Suggest</strong>.
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
                          <span className="text-xs font-mono text-blue-400">{m.technique.mitre_id}</span>
                          <span className="text-sm font-medium text-white truncate">{m.technique.name}</span>
                          {m.auto_mapped && (
                            <span className="text-xs bg-purple-900/40 border border-purple-800 text-purple-400 px-1.5 py-0.5 rounded">AI</span>
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
                        {removingId === m.technique_id
                          ? <Loader2 className="w-4 h-4 animate-spin" />
                          : <Trash2 className="w-4 h-4" />}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* â”€â”€ Browse Matrix tab â”€â”€ */}
          {tab === 'matrix' && (
            <div className="flex flex-col flex-1 min-h-0">
              {/* Toolbar */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 shrink-0">
                <div className="relative flex-1 max-w-xs">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Filter techniquesâ€¦"
                    value={matrixFilter}
                    onChange={e => setMatrixFilter(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <p className="text-xs text-gray-500">
                  {mappings.length} mapped &middot; Click a cell to add or remove
                </p>
                <div className="flex items-center gap-3 ml-auto text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full border border-green-500 bg-green-500/20 inline-block" />
                    Mapped
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full border border-gray-600 inline-block" />
                    Not mapped
                  </span>
                </div>
              </div>

              {/* Matrix grid */}
              <div className="flex-1 overflow-x-auto overflow-y-hidden">
                {loadingTactics ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-500 mr-2" />
                    <span className="text-gray-500 text-sm">Loading ATT&amp;CK frameworkâ€¦</span>
                  </div>
                ) : (
                  <div className="flex gap-2 p-4 h-full" style={{ minWidth: 'max-content' }}>
                    {matrixTactics.map(tactic => (
                      <TacticColumn
                        key={tactic.id}
                        tactic={tactic}
                        techniques={techniquesByTactic.get(tactic.id)}
                        loading={loadingTechIds.has(tactic.id)}
                        mappedIds={mappedTechniqueIds}
                        togglingId={togglingId}
                        filter={matrixFilter}
                        onToggle={handleToggleTechnique}
                        onVisible={handleTacticVisible}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* â”€â”€ AI Suggestions tab â”€â”€ */}
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
                  {autoMapping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                  {autoMapping ? 'Analysingâ€¦' : 'Run AI Mapping'}
                </button>
              </div>

              {aiError && (
                <div className="text-red-400 text-sm flex items-center gap-2 bg-red-900/20 border border-red-800 rounded-lg p-3">
                  <AlertCircle className="w-4 h-4" />{aiError}
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
                    const alreadyMapped = mappings.some(m => m.technique?.mitre_id === s.mitre_id);
                    const isAccepted = acceptedIds.has(s.mitre_id);
                    const isRejected = rejectedIds.has(s.mitre_id);
                    return (
                      <div
                        key={s.mitre_id}
                        className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                          alreadyMapped || isAccepted ? 'bg-green-900/20 border-green-800'
                          : isRejected ? 'bg-gray-800/30 border-gray-700 opacity-50'
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
                            <button onClick={() => acceptSuggestion(s)} className="text-green-400 hover:text-green-300 transition-colors" title="Accept">
                              <CheckCircle className="w-5 h-5" />
                            </button>
                            <button onClick={() => setRejectedIds(p => new Set([...p, s.mitre_id]))} className="text-gray-600 hover:text-red-400 transition-colors" title="Reject">
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

          {/* â”€â”€ Search & Add tab â”€â”€ */}
          {tab === 'search' && (
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search by technique name or MITRE IDâ€¦"
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
                      <div key={t.id} className="flex items-center gap-3 bg-gray-800/60 border border-gray-700 rounded-lg px-3 py-2.5">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-blue-400 flex-shrink-0">{t.mitre_id}</span>
                            <span className="text-sm text-white truncate">{t.name}</span>
                            {t.is_subtechnique && <span className="text-xs text-gray-600 flex-shrink-0">sub</span>}
                          </div>
                          {t.tactic_shortname && (
                            <p className="text-xs text-gray-500 mt-0.5">{t.tactic_shortname}</p>
                          )}
                        </div>
                        {alreadyMapped ? (
                          <span className="text-xs text-green-400 flex items-center gap-1 flex-shrink-0">
                            <CheckCircle className="w-3.5 h-3.5" />Mapped
                          </span>
                        ) : (
                          <button
                            onClick={() => handleAddTechnique(t)}
                            disabled={addingId === t.id}
                            className="text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white px-3 py-1 rounded-md transition-colors flex-shrink-0"
                          >
                            {addingId === t.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Add'}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {searchQuery.length >= 2 && !searching && searchResults.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-4">No techniques found for &ldquo;{searchQuery}&rdquo;</p>
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
        <div className="p-4 border-t border-gray-800 flex items-center justify-between shrink-0">
          <p className="text-xs text-gray-600">
            {mappings.length} technique{mappings.length !== 1 ? 's' : ''} mapped to this threat
          </p>
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

