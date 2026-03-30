'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, AlertTriangle, Shield, TrendingUp, Plus, Brain } from 'lucide-react';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Alert } from '../components/Alert';
import apiClient from '../lib/api-client';
import { Assessment, ActiveRisk, MLModelInfo, Threat, ComplianceSummary } from '../lib/types';
import { StatusBadge } from '../components/Badge';
import { format } from 'date-fns';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalAssessments: 0,
    activeRisks: 0,
    criticalThreats: 0,
  });
  const [recentAssessments, setRecentAssessments] = useState<Assessment[]>([]);
  const [topRisks, setTopRisks] = useState<ActiveRisk[]>([]);
  const [mlModel, setMlModel] = useState<MLModelInfo | null>(null);
  const [allThreats, setAllThreats] = useState<Threat[]>([]);
  const [complianceSummary, setComplianceSummary] = useState<ComplianceSummary[]>([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load stats and recent data
      const [assessmentsResponse, risksResponse, mlModelInfo, threatsResponse, complianceResponse] = await Promise.all([
        apiClient.getAssessments({ limit: 5 }),
        apiClient.getActiveRisks({ status: 'open' }).catch(() => []),
        apiClient.getMLModelInfo().catch(() => null),
        apiClient.getAllThreats({ limit: 500 }).catch(() => []),
        apiClient.getComplianceSummary().catch(() => []),
      ]);

      const assessments = assessmentsResponse;
      const risks = risksResponse;
      setMlModel(mlModelInfo);
      setAllThreats(threatsResponse);
      setComplianceSummary(complianceResponse);

      setStats({
        totalAssessments: assessments.length,
        activeRisks: risks.filter((r: ActiveRisk) => r.status === 'open').length,
        criticalThreats: risks.filter((r: ActiveRisk) => r.residual_risk === 'Critical').length,
      });

      setRecentAssessments(assessments.slice(0, 5));
      setTopRisks(risks.slice(0, 5));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Overview of your threat risk assessments</p>
        </div>
        <Link href="/assessments/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Assessment
          </Button>
        </Link>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Assessments</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalAssessments}</p>
            </div>
            <div className="bg-blue-100 rounded-lg p-3">
              <FileText className="w-8 h-8 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Risks</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.activeRisks}</p>
            </div>
            <div className="bg-yellow-100 rounded-lg p-3">
              <AlertTriangle className="w-8 h-8 text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Critical Threats</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.criticalThreats}</p>
            </div>
            <div className="bg-red-100 rounded-lg p-3">
              <Shield className="w-8 h-8 text-red-600" />
            </div>
          </div>
        </div>

        <Link href="/intelligence" className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">ML Model</p>
              <p className={`text-xl font-bold mt-2 ${mlModel?.trained ? 'text-green-600' : 'text-amber-600'}`}>
                {mlModel?.trained ? 'Trained' : 'Not Trained'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {mlModel?.trained ? `${mlModel.algorithm} · ${mlModel.feature_count} features` : 'Click to configure'}
              </p>
            </div>
            <div className="bg-purple-100 rounded-lg p-3">
              <Brain className="w-8 h-8 text-purple-600" />
            </div>
          </div>
        </Link>
      </div>

      {/* Risk Heatmap + Compliance Posture */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Risk Heatmap */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Risk Heatmap</h2>
            <p className="text-xs text-gray-500 mt-0.5">Likelihood × Impact distribution across all threats</p>
          </div>
          <div className="p-6">
            <RiskHeatmap threats={allThreats} />
          </div>
        </div>

        {/* Compliance Posture */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Compliance Posture</h2>
            <p className="text-xs text-gray-500 mt-0.5">Framework compliance overview</p>
          </div>
          <div className="p-6">
            {complianceSummary.length === 0 ? (
              <p className="text-center text-gray-500 py-8 text-sm">No compliance frameworks configured yet</p>
            ) : (
              <div className="space-y-4">
                {complianceSummary.map(s => (
                  <div key={s.framework_id}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="font-medium text-gray-900">{s.framework_name}</span>
                      <span className={`font-bold ${
                        s.compliance_pct >= 80 ? 'text-green-600' : s.compliance_pct >= 50 ? 'text-amber-600' : 'text-red-600'
                      }`}>{s.compliance_pct}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div
                        className={`rounded-full h-2.5 transition-all ${
                          s.compliance_pct >= 80 ? 'bg-green-500' : s.compliance_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(s.compliance_pct, 100)}%` }}
                      />
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{s.total_controls} controls</span>
                      <span className="text-green-600">{s.compliant} ✓</span>
                      <span className="text-red-600">{s.non_compliant} ✗</span>
                      <span className="text-amber-600">{s.partially_compliant} ~</span>
                      <span>{s.not_assessed} unassessed</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Assessments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Assessments</h2>
          </div>
          <div className="p-6">
            {recentAssessments.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No assessments yet</p>
            ) : (
              <div className="space-y-4">
                {recentAssessments.map((assessment) => {
                  const assessThreats = allThreats.filter(t => t.assessment_id === assessment.id);
                  const sevCounts = assessThreats.reduce((acc, t) => {
                    const s = t.severity || 'Medium';
                    acc[s] = (acc[s] || 0) + 1;
                    return acc;
                  }, {} as Record<string, number>);
                  const total = assessThreats.length;
                  return (
                  <Link
                    key={assessment.id}
                    href={`/assessments/${assessment.id}`}
                    className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900">{assessment.title || 'Untitled Assessment'}</h3>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {assessment.description || 'No description'}
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          {format(new Date(assessment.created_at), 'MMM d, yyyy')}
                        </p>
                      </div>
                      <StatusBadge status={assessment.status} />
                    </div>
                    {/* Severity distribution mini-bar */}
                    {total > 0 && (
                      <div className="mt-2.5">
                        <div className="flex h-1.5 rounded-full overflow-hidden">
                          {(sevCounts['Critical'] || 0) > 0 && (
                            <div className="bg-red-600" style={{ width: `${(sevCounts['Critical'] / total) * 100}%` }} />
                          )}
                          {(sevCounts['High'] || 0) > 0 && (
                            <div className="bg-amber-500" style={{ width: `${(sevCounts['High'] / total) * 100}%` }} />
                          )}
                          {(sevCounts['Medium'] || 0) > 0 && (
                            <div className="bg-orange-400" style={{ width: `${(sevCounts['Medium'] / total) * 100}%` }} />
                          )}
                          {(sevCounts['Low'] || 0) > 0 && (
                            <div className="bg-blue-500" style={{ width: `${(sevCounts['Low'] / total) * 100}%` }} />
                          )}
                        </div>
                        <p className="text-[10px] text-gray-400 mt-1">
                          {total} threat{total !== 1 ? 's' : ''}
                          {(sevCounts['Critical'] || 0) > 0 ? ` · ${sevCounts['Critical']} crit` : ''}
                          {(sevCounts['High'] || 0) > 0 ? ` · ${sevCounts['High']} high` : ''}
                        </p>
                      </div>
                    )}
                  </Link>
                  );
                })}
              </div>
            )}
            <div className="mt-4 text-center">
              <Link href="/assessments" className="text-sm text-primary hover:underline">
                View all assessments →
              </Link>
            </div>
          </div>
        </div>

        {/* Top Risks */}
        <div className="bg-white rounded-lg border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Top Open Risks</h2>
          </div>
          <div className="p-6">
            {topRisks.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No open risks</p>
            ) : (
              <div className="space-y-4">
                {topRisks.map((risk) => (
                  <Link
                    key={risk.id}
                    href={`/active-risks/${risk.id}`}
                    className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900 line-clamp-2">
                          {risk.title}
                        </h3>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs text-gray-500">
                            Severity: {risk.residual_risk}
                          </span>
                          <span className="text-xs text-gray-300">•</span>
                          <span className="text-xs text-gray-500">
                            {format(new Date(risk.created_at), 'MMM d, yyyy')}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
            <div className="mt-4 text-center">
              <Link href="/active-risks" className="text-sm text-primary hover:underline">
                View risk register →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Risk Heatmap ─────────────────────────────────────────────────────────────

const LEVELS = ['Critical', 'High', 'Medium', 'Low'] as const;

const CELL_COLORS: Record<string, string> = {
  '0': 'bg-gray-50',
  '1': 'bg-yellow-100',
  '2': 'bg-yellow-200',
  '3': 'bg-orange-300',
  '4': 'bg-orange-400',
  '5+': 'bg-red-500 text-white',
};

function getCellColor(count: number): string {
  if (count === 0) return CELL_COLORS['0'];
  if (count <= 1) return CELL_COLORS['1'];
  if (count <= 2) return CELL_COLORS['2'];
  if (count <= 3) return CELL_COLORS['3'];
  if (count <= 4) return CELL_COLORS['4'];
  return CELL_COLORS['5+'];
}

function RiskHeatmap({ threats }: { threats: Threat[] }) {
  // Build likelihood × impact matrix
  const matrix: Record<string, Record<string, number>> = {};
  for (const l of LEVELS) {
    matrix[l] = {};
    for (const i of LEVELS) {
      matrix[l][i] = 0;
    }
  }
  for (const t of threats) {
    const likelihood = t.likelihood || 'Medium';
    const impact = t.impact || 'Medium';
    if (matrix[likelihood]?.[impact] !== undefined) {
      matrix[likelihood][impact]++;
    }
  }

  if (threats.length === 0) {
    return <p className="text-center text-gray-500 py-8 text-sm">No threats to display</p>;
  }

  return (
    <div>
      <div className="flex">
        {/* Y-axis label */}
        <div className="flex flex-col justify-center mr-2">
          <span className="text-xs text-gray-500 font-medium -rotate-90 whitespace-nowrap">Likelihood →</span>
        </div>
        <div className="flex-1">
          {/* Header row */}
          <div className="grid grid-cols-5 gap-1 mb-1">
            <div />
            {LEVELS.slice().reverse().map(imp => (
              <div key={imp} className="text-center text-xs text-gray-500 font-medium py-1">{imp}</div>
            ))}
          </div>
          {/* Data rows (Critical likelihood at top) */}
          {LEVELS.map(likelihood => (
            <div key={likelihood} className="grid grid-cols-5 gap-1 mb-1">
              <div className="flex items-center justify-end pr-2 text-xs text-gray-500 font-medium">{likelihood}</div>
              {LEVELS.slice().reverse().map(impact => {
                const count = matrix[likelihood][impact];
                return (
                  <div
                    key={`${likelihood}-${impact}`}
                    className={`aspect-square rounded flex items-center justify-center text-sm font-bold ${getCellColor(count)}`}
                    title={`${likelihood} likelihood × ${impact} impact: ${count} threats`}
                  >
                    {count > 0 ? count : ''}
                  </div>
                );
              })}
            </div>
          ))}
          <div className="text-center text-xs text-gray-500 font-medium mt-1">Impact →</div>
        </div>
      </div>
      <div className="flex items-center justify-center gap-2 mt-3 text-xs text-gray-500">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-50 border border-gray-200" /> 0</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-200" /> 1-2</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-400" /> 3-4</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500" /> 5+</span>
      </div>
    </div>
  );
}
