'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, AlertTriangle, Shield, Plus, Brain, ArrowRight, ClipboardCheck } from 'lucide-react';
import { Button } from '../components/Button';
import { SkeletonDashboard } from '../components/LoadingSpinner';
import { Alert } from '../components/Alert';
import { EmptyState } from '../components/EmptyState';
import { SeverityBadge } from '../components/Badge';
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
    return <SkeletonDashboard />;
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Overview of your threat risk assessments</p>
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <StatCard
          label="Total Assessments"
          value={stats.totalAssessments}
          icon={FileText}
          iconBg="bg-blue-100 dark:bg-blue-900/30"
          iconColor="text-blue-600 dark:text-blue-400"
          href="/assessments"
          subtitle="View all assessments"
        />
        <StatCard
          label="Active Risks"
          value={stats.activeRisks}
          icon={AlertTriangle}
          iconBg="bg-amber-100 dark:bg-amber-900/30"
          iconColor="text-amber-600 dark:text-amber-400"
          alert={stats.activeRisks > 0}
          href="/active-risks"
          subtitle="View risk register"
        />
        <StatCard
          label="Critical Threats"
          value={stats.criticalThreats}
          icon={Shield}
          iconBg="bg-red-100 dark:bg-red-900/30"
          iconColor="text-red-600 dark:text-red-400"
          alert={stats.criticalThreats > 0}
          href="/assessments"
          subtitle="View threat details"
        />
        <StatCard
          label="ML Model"
          value={mlModel?.trained ? 'Trained' : 'Not Trained'}
          icon={Brain}
          iconBg="bg-purple-100 dark:bg-purple-900/30"
          iconColor="text-purple-600 dark:text-purple-400"
          href="/intelligence"
          subtitle={mlModel?.trained ? `${mlModel.algorithm} · ${mlModel.feature_count} features` : 'Click to configure'}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Link href="/assessments/new" className="group flex items-center gap-3 p-4 rounded-xl border border-border bg-card hover:border-primary/30 hover:shadow-md transition-all duration-200">
          <div className="bg-primary/10 rounded-lg p-2"><FileText className="w-5 h-5 text-primary" /></div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">New Assessment</p>
            <p className="text-xs text-muted-foreground">Start a risk assessment</p>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </Link>
        <Link href="/active-risks" className="group flex items-center gap-3 p-4 rounded-xl border border-border bg-card hover:border-primary/30 hover:shadow-md transition-all duration-200">
          <div className="bg-amber-500/10 rounded-lg p-2"><AlertTriangle className="w-5 h-5 text-amber-500" /></div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">Risk Register</p>
            <p className="text-xs text-muted-foreground">Manage active risks</p>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </Link>
        <Link href="/compliance" className="group flex items-center gap-3 p-4 rounded-xl border border-border bg-card hover:border-primary/30 hover:shadow-md transition-all duration-200">
          <div className="bg-emerald-500/10 rounded-lg p-2"><ClipboardCheck className="w-5 h-5 text-emerald-500" /></div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">Compliance</p>
            <p className="text-xs text-muted-foreground">Review framework posture</p>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </Link>
      </div>

      {/* Risk Heatmap + Compliance Posture */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-xl border border-border shadow-sm">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="text-base font-semibold text-foreground">Risk Heatmap</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Likelihood × Impact distribution across all threats</p>
          </div>
          <div className="p-6">
            <RiskHeatmap threats={allThreats} />
          </div>
        </div>

        <div className="bg-card rounded-xl border border-border shadow-sm">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="text-base font-semibold text-foreground">Compliance Posture</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Framework compliance overview</p>
          </div>
          <div className="p-6">
            {complianceSummary.length === 0 ? (
              <p className="text-center text-muted-foreground py-8 text-sm">No compliance frameworks configured yet</p>
            ) : (
              <div className="space-y-5">
                {complianceSummary.map(s => (
                  <div key={s.framework_id}>
                    <div className="flex items-center justify-between text-sm mb-1.5">
                      <span className="font-medium text-foreground">{s.framework_name}</span>
                      <span className={`font-bold ${
                        s.compliance_pct >= 80 ? 'text-emerald-600 dark:text-emerald-400' : s.compliance_pct >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'
                      }`}>{s.compliance_pct}%</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className={`rounded-full h-2 transition-all duration-500 ${
                          s.compliance_pct >= 80 ? 'bg-emerald-500' : s.compliance_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(s.compliance_pct, 100)}%` }}
                      />
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span>{s.total_controls} controls</span>
                      <span className="text-emerald-600 dark:text-emerald-400">{s.compliant} ✓</span>
                      <span className="text-red-600 dark:text-red-400">{s.non_compliant} ✗</span>
                      <span className="text-amber-600 dark:text-amber-400">{s.partially_compliant} ~</span>
                      <span>{s.not_assessed} unassessed</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Assessments + Top Risks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-xl border border-border shadow-sm">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Recent Assessments</h2>
            <Link href="/assessments" className="text-xs text-primary hover:underline">
              View all →
            </Link>
          </div>
          <div className="p-4">
            {recentAssessments.length === 0 ? (
              <EmptyState
                icon="assessments"
                title="No assessments yet"
                description="Create your first assessment to get started"
                actionLabel="New Assessment"
                onAction={() => window.location.href = '/assessments/new'}
              />
            ) : (
              <div className="space-y-2">
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
                      className="block p-4 rounded-xl hover:bg-muted/50 transition-all duration-200 group"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-foreground group-hover:text-primary transition-colors truncate">
                            {assessment.title || 'Untitled Assessment'}
                          </h3>
                          <p className="text-sm text-muted-foreground mt-0.5 line-clamp-1">
                            {assessment.description || 'No description'}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1.5">
                            {format(new Date(assessment.created_at), 'MMM d, yyyy')}
                          </p>
                        </div>
                        <StatusBadge status={assessment.status} />
                      </div>
                      {total > 0 && (
                        <div className="mt-2.5">
                          <div className="flex h-1.5 rounded-full overflow-hidden bg-muted">
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
                          <p className="text-[10px] text-muted-foreground mt-1">
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
          </div>
        </div>

        <div className="bg-card rounded-xl border border-border shadow-sm">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Top Open Risks</h2>
            <Link href="/active-risks" className="text-xs text-primary hover:underline">
              View all →
            </Link>
          </div>
          <div className="p-4">
            {topRisks.length === 0 ? (
              <EmptyState
                icon="risks"
                title="No open risks"
                description="All clear — no active risks in the register"
              />
            ) : (
              <div className="space-y-2">
                {topRisks.map((risk) => (
                  <Link
                    key={risk.id}
                    href="/active-risks"
                    className="flex items-start gap-3 p-4 rounded-xl hover:bg-muted/50 transition-all duration-200 group"
                  >
                    <div className="mt-0.5">
                      <SeverityBadge severity={risk.residual_risk || 'Medium'} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-foreground group-hover:text-primary transition-colors line-clamp-2">
                        {risk.title}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {format(new Date(risk.created_at), 'MMM d, yyyy')}
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon: Icon,
  iconBg,
  iconColor,
  alert = false,
  href,
  subtitle,
}: {
  label: string;
  value: number | string;
  icon: typeof FileText;
  iconBg: string;
  iconColor: string;
  alert?: boolean;
  href?: string;
  subtitle?: string;
}) {
  const content = (
    <div className="bg-card rounded-xl border border-border p-6 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 h-full">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className={`text-3xl font-bold mt-2 animate-count-up ${alert ? 'text-red-600 dark:text-red-400' : 'text-foreground'}`}>
            {value}
          </p>
          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
        </div>
        <div className={`${iconBg} rounded-xl p-3 group-hover:scale-110 transition-transform duration-200`}>
          <Icon className={`w-7 h-7 ${iconColor}`} />
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link href={href} className="group">{content}</Link>;
  }
  return content;
}

// ── Risk Heatmap ─────────────────────────────────────────────────────────────

const LEVELS = ['Critical', 'High', 'Medium', 'Low'] as const;

function getCellColor(count: number): string {
  if (count === 0) return 'bg-muted/50';
  if (count <= 1) return 'bg-yellow-200 dark:bg-yellow-900/40 text-yellow-900 dark:text-yellow-200';
  if (count <= 2) return 'bg-orange-300 dark:bg-orange-900/50 text-orange-900 dark:text-orange-200';
  if (count <= 3) return 'bg-orange-400 dark:bg-orange-800/60 text-white';
  if (count <= 4) return 'bg-red-400 dark:bg-red-800/70 text-white';
  return 'bg-red-600 dark:bg-red-700 text-white';
}

function RiskHeatmap({ threats }: { threats: Threat[] }) {
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
    return <p className="text-center text-muted-foreground py-8 text-sm">No threats to display</p>;
  }

  return (
    <div>
      <div className="flex">
        <div className="flex flex-col justify-center mr-2">
          <span className="text-xs text-muted-foreground font-medium -rotate-90 whitespace-nowrap">Likelihood →</span>
        </div>
        <div className="flex-1">
          <div className="grid grid-cols-5 gap-1.5 mb-1.5">
            <div />
            {LEVELS.slice().reverse().map(imp => (
              <div key={imp} className="text-center text-xs text-muted-foreground font-medium py-1">{imp}</div>
            ))}
          </div>
          {LEVELS.map(likelihood => (
            <div key={likelihood} className="grid grid-cols-5 gap-1.5 mb-1.5">
              <div className="flex items-center justify-end pr-2 text-xs text-muted-foreground font-medium">{likelihood}</div>
              {LEVELS.slice().reverse().map(impact => {
                const count = matrix[likelihood][impact];
                return (
                  <div
                    key={`${likelihood}-${impact}`}
                    className={`aspect-square rounded-lg flex items-center justify-center text-sm font-bold transition-all duration-200 hover:scale-105 ${getCellColor(count)}`}
                    title={`${likelihood} likelihood × ${impact} impact: ${count} threats`}
                  >
                    {count > 0 ? count : ''}
                  </div>
                );
              })}
            </div>
          ))}
          <div className="text-center text-xs text-muted-foreground font-medium mt-1">Impact →</div>
        </div>
      </div>
      <div className="flex items-center justify-center gap-3 mt-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-muted/50 border border-border" /> 0</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-200 dark:bg-yellow-900/40" /> 1-2</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-400 dark:bg-orange-800/60" /> 3-4</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-600 dark:bg-red-700" /> 5+</span>
      </div>
    </div>
  );
}
