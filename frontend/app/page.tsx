'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, AlertTriangle, Shield, TrendingUp, Plus } from 'lucide-react';
import { Button } from '@/components/Button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Alert } from '@/components/Alert';
import apiClient from '@/lib/api-client';
import { Assessment, ActiveRisk } from '@/lib/types';
import { StatusBadge } from '@/components/Badge';
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

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load stats and recent data
      const [assessmentsResponse, risksResponse] = await Promise.all([
        apiClient.getAssessments({ limit: 5 }),
        apiClient.getActiveRisks({ status: 'open' }),
      ]);

      const assessments = assessmentsResponse as Assessment[];
      const risks = risksResponse as ActiveRisk[];

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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
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
                {recentAssessments.map((assessment) => (
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
                  </Link>
                ))}
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
