'use client';

import { useState, useEffect, useCallback } from 'react';
import { Shield, CheckCircle, XCircle, AlertCircle, MinusCircle, Loader2, ChevronDown, ChevronRight, Zap, AlertTriangle } from 'lucide-react';
import apiClient from '../lib/api-client';
import type { ComplianceFramework, ComplianceControl, ComplianceMapping, ComplianceSummary, ComplianceGaps } from '../lib/types';

// ── Status helpers ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: typeof CheckCircle }> = {
  compliant: { label: 'Compliant', color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/30', icon: CheckCircle },
  non_compliant: { label: 'Non-Compliant', color: 'text-red-700 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30', icon: XCircle },
  partially_compliant: { label: 'Partial', color: 'text-amber-700 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30', icon: AlertCircle },
  not_applicable: { label: 'N/A', color: 'text-muted-foreground', bg: 'bg-muted', icon: MinusCircle },
  not_assessed: { label: 'Not Assessed', color: 'text-muted-foreground/60', bg: 'bg-muted/50', icon: MinusCircle },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.not_assessed;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function ProgressBar({ value, color = 'bg-green-500' }: { value: number; color?: string }) {
  return (
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
      <div className={`${color} rounded-full h-2 transition-all`} style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  );
}

function ConfidenceBadge({ score }: { score?: number }) {
  if (score == null) return null;
  const color = score >= 90 ? 'text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20' : score >= 70 ? 'text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20' : 'text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${color}`}>{score}%</span>;
}

function MappedByTag({ mappedBy }: { mappedBy?: string }) {
  if (!mappedBy || mappedBy === 'manual') return null;
  const label = mappedBy === 'auto_static' ? 'Static' : 'AI';
  const cls = mappedBy === 'auto_static' ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20';
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${cls}`}>{label}</span>;
}

// ── Main Panel ─────────────────────────────────────────────────────────────

interface CompliancePanelProps {
  assessmentId: string;
  threatIds?: string[];
}

export function CompliancePanel({ assessmentId, threatIds = [] }: CompliancePanelProps) {
  const [summaries, setSummaries] = useState<ComplianceSummary[]>([]);
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([]);
  const [selectedFw, setSelectedFw] = useState<string | null>(null);
  const [controls, setControls] = useState<ComplianceControl[]>([]);
  const [mappings, setMappings] = useState<ComplianceMapping[]>([]);
  const [expandedFamily, setExpandedFamily] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [autoMapping, setAutoMapping] = useState(false);
  const [autoMapResult, setAutoMapResult] = useState<string | null>(null);
  const [gaps, setGaps] = useState<ComplianceGaps | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [fws, sums] = await Promise.all([
        apiClient.listComplianceFrameworks(),
        apiClient.getComplianceSummary(assessmentId),
      ]);
      setFrameworks(fws);
      setSummaries(sums);
      if (fws.length > 0 && !selectedFw) {
        setSelectedFw(fws[0].id);
      }
    } catch {
      // frameworks not seeded yet
      setFrameworks([]);
      setSummaries([]);
    } finally {
      setLoading(false);
    }
  }, [assessmentId, selectedFw]);

  useEffect(() => { loadData(); }, [loadData]);

  // Load controls + mappings when framework selected
  useEffect(() => {
    if (!selectedFw) return;
    (async () => {
      try {
        const [ctrls, maps] = await Promise.all([
          apiClient.listComplianceControls(selectedFw),
          apiClient.listComplianceMappings({ assessment_id: assessmentId, framework_id: selectedFw }),
        ]);
        setControls(ctrls);
        setMappings(maps);
      } catch {
        setControls([]);
        setMappings([]);
      }
    })();
  }, [selectedFw, assessmentId]);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await apiClient.seedComplianceFrameworks();
      await loadData();
    } finally {
      setSeeding(false);
    }
  };

  const handleStatusChange = async (controlId: string, newStatus: string) => {
    setSavingId(controlId);
    try {
      const existing = mappings.find(m => m.control_id === controlId);
      if (existing) {
        const updated = await apiClient.updateComplianceMapping(existing.id, { status: newStatus });
        setMappings(prev => prev.map(m => m.id === existing.id ? updated : m));
      } else {
        const created = await apiClient.createComplianceMapping({
          control_id: controlId,
          assessment_id: assessmentId,
          status: newStatus,
          mapped_by: 'manual',
        });
        setMappings(prev => [...prev, created]);
      }
      // Refresh summary
      const sums = await apiClient.getComplianceSummary(assessmentId);
      setSummaries(sums);
    } finally {
      setSavingId(null);
    }
  };

  const handleAutoMap = async () => {
    if (!selectedFw || threatIds.length === 0) return;
    const fw = frameworks.find(f => f.id === selectedFw);
    if (!fw) return;

    setAutoMapping(true);
    setAutoMapResult(null);
    let totalSaved = 0;
    try {
      for (const tid of threatIds) {
        const res = await apiClient.autoMapCompliance(tid, fw.key, assessmentId);
        totalSaved += res.saved_count;
      }
      setAutoMapResult(`Mapped ${totalSaved} control(s) across ${threatIds.length} threat(s)`);
      // Reload controls, mappings, summaries
      if (selectedFw) {
        const [ctrls, maps, sums] = await Promise.all([
          apiClient.listComplianceControls(selectedFw),
          apiClient.listComplianceMappings({ assessment_id: assessmentId, framework_id: selectedFw }),
          apiClient.getComplianceSummary(assessmentId),
        ]);
        setControls(ctrls);
        setMappings(maps);
        setSummaries(sums);
      }
    } catch {
      setAutoMapResult('Auto-mapping failed — check backend logs');
    } finally {
      setAutoMapping(false);
    }
  };

  // Load gaps when framework changes
  useEffect(() => {
    if (!selectedFw) return;
    const fw = frameworks.find(f => f.id === selectedFw);
    if (!fw) return;
    apiClient.getComplianceGaps(fw.key, assessmentId).then(setGaps).catch(() => setGaps(null));
  }, [selectedFw, frameworks, assessmentId, mappings]);

  // Group controls by family
  const families = controls.reduce<Record<string, ComplianceControl[]>>((acc, ctrl) => {
    const fam = ctrl.family || 'Uncategorized';
    (acc[fam] = acc[fam] || []).push(ctrl);
    return acc;
  }, {});

  const mappingByControl = mappings.reduce<Record<string, ComplianceMapping>>((acc, m) => {
    acc[m.control_id] = m;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading compliance data…
      </div>
    );
  }

  // Seed prompt if no frameworks exist
  if (frameworks.length === 0) {
    return (
      <div className="text-center py-12">
        <Shield className="w-12 h-12 mx-auto mb-3 text-muted-foreground/30" />
        <h3 className="text-lg font-medium text-foreground mb-1">No Compliance Frameworks</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Seed standard frameworks (NIST 800-53, ISO 27001, CIS v8) to start mapping controls.
        </p>
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
          Seed Frameworks
        </button>
      </div>
    );
  }

  const currentSummary = summaries.find(s => s.framework_id === selectedFw);

  return (
    <div className="space-y-4">
      {/* Framework Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {summaries.map(s => (
          <button
            key={s.framework_id}
            onClick={() => setSelectedFw(s.framework_id)}
            className={`text-left p-4 rounded-lg border-2 transition-colors ${
              selectedFw === s.framework_id
                ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                : 'border-border bg-card hover:border-primary/30'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-foreground truncate">{s.framework_name}</h4>
              <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400">{s.compliance_pct}%</span>
            </div>
            <ProgressBar
              value={s.compliance_pct}
              color={s.compliance_pct >= 80 ? 'bg-green-500' : s.compliance_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}
            />
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              <span className="text-green-600">{s.compliant} ✓</span>
              <span className="text-red-600">{s.non_compliant} ✗</span>
              <span className="text-amber-600">{s.partially_compliant} ~</span>
              <span>{s.not_assessed} ?</span>
              {s.gap_controls > 0 && (
                <span className="text-orange-600 flex items-center gap-0.5">
                  <AlertTriangle className="w-3 h-3" /> {s.gap_controls} gaps
                </span>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Auto-Map Bar */}
      {currentSummary && threatIds.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800/40">
          <button
            onClick={handleAutoMap}
            disabled={autoMapping}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {autoMapping ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            Auto-Map {threatIds.length} Threat{threatIds.length > 1 ? 's' : ''}
          </button>
          <span className="text-xs text-indigo-700 dark:text-indigo-400">
            Maps threats to {currentSummary.framework_name} controls (static + AI)
          </span>
          {autoMapResult && (
            <span className="ml-auto text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded">{autoMapResult}</span>
          )}
        </div>
      )}

      {/* Gap Summary */}
      {gaps && gaps.gap_count > 0 && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800/40 rounded-lg px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
            <span className="text-sm font-medium text-orange-800 dark:text-orange-300">
              {gaps.gap_count} Unmapped Control{gaps.gap_count > 1 ? 's' : ''} (Compliance Gaps)
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {gaps.gap_controls.slice(0, 20).map(g => (
              <span key={g.control_id} className="text-[10px] px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 font-mono">
                {g.control_id}
              </span>
            ))}
            {gaps.gap_count > 20 && (
              <span className="text-[10px] text-orange-500 dark:text-orange-400">+{gaps.gap_count - 20} more</span>
            )}
          </div>
        </div>
      )}

      {/* Controls by Family */}
      {currentSummary && (
        <div className="border border-border rounded-lg divide-y divide-border">
          {Object.entries(families).map(([family, ctrls]) => {
            const isExpanded = expandedFamily === family;
            const familyMapped = ctrls.filter(c => mappingByControl[c.id]).length;
            return (
              <div key={family}>
                <button
                  onClick={() => setExpandedFamily(isExpanded ? null : family)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    <span className="text-sm font-medium text-foreground">{family}</span>
                    <span className="text-xs text-muted-foreground">({familyMapped}/{ctrls.length} mapped)</span>
                  </div>
                </button>
                {isExpanded && (
                  <div className="bg-muted px-4 pb-3">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-muted-foreground border-b border-border">
                          <th className="text-left py-2 font-medium w-24">Control</th>
                          <th className="text-left py-2 font-medium">Title</th>
                          <th className="text-left py-2 font-medium w-20">Source</th>
                          <th className="text-left py-2 font-medium w-40">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ctrls.map(ctrl => {
                          const mapping = mappingByControl[ctrl.id];
                          const currentStatus = mapping?.status || 'not_assessed';
                          return (
                            <tr key={ctrl.id} className="border-b border-border/50 last:border-0">
                              <td className="py-2 font-mono text-xs text-muted-foreground">{ctrl.control_id}</td>
                              <td className="py-2 text-foreground">{ctrl.title}</td>
                              <td className="py-2">
                                <div className="flex items-center gap-1">
                                  <MappedByTag mappedBy={mapping?.mapped_by} />
                                  <ConfidenceBadge score={mapping?.confidence_score} />
                                </div>
                              </td>
                              <td className="py-2">
                                {savingId === ctrl.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                                ) : (
                                  <select
                                    value={currentStatus}
                                    onChange={e => handleStatusChange(ctrl.id, e.target.value)}
                                    className={`text-xs rounded px-2 py-1 border border-border focus:ring-1 focus:ring-indigo-500 ${
                                      currentStatus === 'compliant' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400' :
                                      currentStatus === 'non_compliant' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400' :
                                      currentStatus === 'partially_compliant' ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400' :
                                      'bg-background text-muted-foreground'
                                    }`}
                                  >
                                    <option value="not_assessed">Not Assessed</option>
                                    <option value="compliant">Compliant</option>
                                    <option value="non_compliant">Non-Compliant</option>
                                    <option value="partially_compliant">Partial</option>
                                    <option value="not_applicable">N/A</option>
                                  </select>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
