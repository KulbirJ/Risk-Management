'use client';

import { useState, useEffect } from 'react';
import { Shield, Loader2, ChevronDown, ChevronRight, Download, Plus } from 'lucide-react';
import apiClient from '../../lib/api-client';
import type { ComplianceFramework, ComplianceControl, ComplianceMapping, ComplianceSummary } from '../../lib/types';

const STATUS_OPTIONS = [
  { value: 'not_assessed', label: 'Not Assessed', color: 'bg-gray-100 text-gray-600' },
  { value: 'compliant', label: 'Compliant', color: 'bg-green-100 text-green-700' },
  { value: 'non_compliant', label: 'Non-Compliant', color: 'bg-red-100 text-red-700' },
  { value: 'partially_compliant', label: 'Partial', color: 'bg-amber-100 text-amber-700' },
  { value: 'not_applicable', label: 'N/A', color: 'bg-gray-100 text-gray-500' },
];

export default function CompliancePage() {
  const [frameworks, setFrameworks] = useState<ComplianceFramework[]>([]);
  const [summaries, setSummaries] = useState<ComplianceSummary[]>([]);
  const [selectedFw, setSelectedFw] = useState<string | null>(null);
  const [controls, setControls] = useState<ComplianceControl[]>([]);
  const [mappings, setMappings] = useState<ComplianceMapping[]>([]);
  const [expandedFamily, setExpandedFamily] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => { loadFrameworks(); }, []);

  const loadFrameworks = async () => {
    setLoading(true);
    try {
      const [fws, sums] = await Promise.all([
        apiClient.listComplianceFrameworks(),
        apiClient.getComplianceSummary(),
      ]);
      setFrameworks(fws);
      setSummaries(sums);
      if (fws.length > 0 && !selectedFw) setSelectedFw(fws[0].id);
    } catch {
      setFrameworks([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!selectedFw) return;
    (async () => {
      const [ctrls, maps] = await Promise.all([
        apiClient.listComplianceControls(selectedFw),
        apiClient.listComplianceMappings({ framework_id: selectedFw }),
      ]);
      setControls(ctrls);
      setMappings(maps);
    })();
  }, [selectedFw]);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await apiClient.seedComplianceFrameworks();
      await loadFrameworks();
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
          status: newStatus,
          mapped_by: 'manual',
        });
        setMappings(prev => [...prev, created]);
      }
      const sums = await apiClient.getComplianceSummary();
      setSummaries(sums);
    } finally {
      setSavingId(null);
    }
  };

  const families = controls.reduce<Record<string, ComplianceControl[]>>((acc, ctrl) => {
    const fam = ctrl.family || 'Uncategorized';
    (acc[fam] = acc[fam] || []).push(ctrl);
    return acc;
  }, {});

  const mappingByControl = mappings.reduce<Record<string, ComplianceMapping>>((acc, m) => {
    acc[m.control_id] = m;
    return acc;
  }, {});

  const currentSummary = summaries.find(s => s.framework_id === selectedFw);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (frameworks.length === 0) {
    return (
      <div className="text-center py-20">
        <Shield className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">No Compliance Frameworks</h2>
        <p className="text-gray-500 mb-6 max-w-md mx-auto">
          Seed standard frameworks (NIST 800-53, ISO 27001, CIS Controls v8) to start tracking compliance posture.
        </p>
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Seed Frameworks
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Compliance</h1>
          <p className="text-gray-600 mt-1">Framework control mapping and posture tracking</p>
        </div>
      </div>

      {/* Framework cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {summaries.map(s => {
          const pctColor = s.compliance_pct >= 80 ? 'text-green-600' : s.compliance_pct >= 50 ? 'text-amber-600' : 'text-red-600';
          const barColor = s.compliance_pct >= 80 ? 'bg-green-500' : s.compliance_pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
          return (
            <button
              key={s.framework_id}
              onClick={() => setSelectedFw(s.framework_id)}
              className={`text-left p-5 rounded-lg border-2 transition-all ${
                selectedFw === s.framework_id
                  ? 'border-indigo-500 bg-indigo-50 shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900">{s.framework_name}</h3>
                <span className={`text-2xl font-bold ${pctColor}`}>{s.compliance_pct}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                <div className={`${barColor} rounded-full h-2 transition-all`} style={{ width: `${s.compliance_pct}%` }} />
              </div>
              <div className="grid grid-cols-4 gap-2 text-xs text-center">
                <div><span className="font-bold text-green-600">{s.compliant}</span><br /><span className="text-gray-500">Compliant</span></div>
                <div><span className="font-bold text-red-600">{s.non_compliant}</span><br /><span className="text-gray-500">Non-Comp</span></div>
                <div><span className="font-bold text-amber-600">{s.partially_compliant}</span><br /><span className="text-gray-500">Partial</span></div>
                <div><span className="font-bold text-gray-500">{s.not_assessed}</span><br /><span className="text-gray-500">Unassessed</span></div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Controls table */}
      {currentSummary && (
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {currentSummary.framework_name} — Controls ({currentSummary.total_controls})
            </h2>
          </div>
          <div className="divide-y divide-gray-200">
            {Object.entries(families).map(([family, ctrls]) => {
              const isExpanded = expandedFamily === family;
              const familyMapped = ctrls.filter(c => mappingByControl[c.id]).length;
              return (
                <div key={family}>
                  <button
                    onClick={() => setExpandedFamily(isExpanded ? null : family)}
                    className="w-full flex items-center justify-between px-6 py-3 hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-2">
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      <span className="font-medium text-gray-900">{family}</span>
                      <span className="text-xs text-gray-400">({familyMapped}/{ctrls.length} mapped)</span>
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="px-6 pb-4">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-xs text-gray-500 border-b border-gray-200">
                            <th className="text-left py-2 w-24">ID</th>
                            <th className="text-left py-2">Title</th>
                            <th className="text-left py-2 w-44">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {ctrls.map(ctrl => {
                            const mapping = mappingByControl[ctrl.id];
                            const currentStatus = mapping?.status || 'not_assessed';
                            const statusOpt = STATUS_OPTIONS.find(o => o.value === currentStatus) || STATUS_OPTIONS[0];
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
                                      className={`text-xs rounded px-2 py-1 border border-gray-300 ${statusOpt.color}`}
                                    >
                                      {STATUS_OPTIONS.map(o => (
                                        <option key={o.value} value={o.value}>{o.label}</option>
                                      ))}
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
        </div>
      )}
    </div>
  );
}
