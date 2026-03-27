'use client';

import { useState, useEffect, useCallback } from 'react';
import { Shield, CheckCircle, XCircle, AlertCircle, MinusCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import apiClient from '../lib/api-client';
import type { ComplianceFramework, ComplianceControl, ComplianceMapping, ComplianceSummary } from '../lib/types';

// ── Status helpers ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: typeof CheckCircle }> = {
  compliant: { label: 'Compliant', color: 'text-green-700', bg: 'bg-green-100', icon: CheckCircle },
  non_compliant: { label: 'Non-Compliant', color: 'text-red-700', bg: 'bg-red-100', icon: XCircle },
  partially_compliant: { label: 'Partial', color: 'text-amber-700', bg: 'bg-amber-100', icon: AlertCircle },
  not_applicable: { label: 'N/A', color: 'text-gray-500', bg: 'bg-gray-100', icon: MinusCircle },
  not_assessed: { label: 'Not Assessed', color: 'text-gray-400', bg: 'bg-gray-50', icon: MinusCircle },
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
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div className={`${color} rounded-full h-2 transition-all`} style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  );
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
      <div className="flex items-center justify-center py-12 text-gray-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading compliance data…
      </div>
    );
  }

  // Seed prompt if no frameworks exist
  if (frameworks.length === 0) {
    return (
      <div className="text-center py-12">
        <Shield className="w-12 h-12 mx-auto mb-3 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-900 mb-1">No Compliance Frameworks</h3>
        <p className="text-sm text-gray-500 mb-4">
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
                ? 'border-indigo-500 bg-indigo-50'
                : 'border-gray-200 bg-white hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-gray-900 truncate">{s.framework_name}</h4>
              <span className="text-lg font-bold text-indigo-600">{s.compliance_pct}%</span>
            </div>
            <ProgressBar
              value={s.compliance_pct}
              color={s.compliance_pct >= 80 ? 'bg-green-500' : s.compliance_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}
            />
            <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
              <span className="text-green-600">{s.compliant} ✓</span>
              <span className="text-red-600">{s.non_compliant} ✗</span>
              <span className="text-amber-600">{s.partially_compliant} ~</span>
              <span>{s.not_assessed} ?</span>
            </div>
          </button>
        ))}
      </div>

      {/* Controls by Family */}
      {currentSummary && (
        <div className="border border-gray-200 rounded-lg divide-y divide-gray-200">
          {Object.entries(families).map(([family, ctrls]) => {
            const isExpanded = expandedFamily === family;
            const familyMapped = ctrls.filter(c => mappingByControl[c.id]).length;
            return (
              <div key={family}>
                <button
                  onClick={() => setExpandedFamily(isExpanded ? null : family)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    <span className="text-sm font-medium text-gray-900">{family}</span>
                    <span className="text-xs text-gray-400">({familyMapped}/{ctrls.length} mapped)</span>
                  </div>
                </button>
                {isExpanded && (
                  <div className="bg-gray-50 px-4 pb-3">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-gray-500 border-b border-gray-200">
                          <th className="text-left py-2 font-medium w-24">Control</th>
                          <th className="text-left py-2 font-medium">Title</th>
                          <th className="text-left py-2 font-medium w-40">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ctrls.map(ctrl => {
                          const mapping = mappingByControl[ctrl.id];
                          const currentStatus = mapping?.status || 'not_assessed';
                          return (
                            <tr key={ctrl.id} className="border-b border-gray-100 last:border-0">
                              <td className="py-2 font-mono text-xs text-gray-600">{ctrl.control_id}</td>
                              <td className="py-2 text-gray-800">{ctrl.title}</td>
                              <td className="py-2">
                                {savingId === ctrl.id ? (
                                  <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                                ) : (
                                  <select
                                    value={currentStatus}
                                    onChange={e => handleStatusChange(ctrl.id, e.target.value)}
                                    className={`text-xs rounded px-2 py-1 border border-gray-300 focus:ring-1 focus:ring-indigo-500 ${
                                      currentStatus === 'compliant' ? 'bg-green-50 text-green-700' :
                                      currentStatus === 'non_compliant' ? 'bg-red-50 text-red-700' :
                                      currentStatus === 'partially_compliant' ? 'bg-amber-50 text-amber-700' :
                                      'bg-white text-gray-600'
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
