'use client';

import { useEffect, useState } from 'react';
import { Brain, Database, Network, Boxes, TrendingUp, Activity, BarChart3, Shield, RefreshCw, ChevronRight } from 'lucide-react';
import { Button } from '../../components/Button';
import { LoadingPage, LoadingSpinner } from '../../components/LoadingSpinner';
import { Alert } from '../../components/Alert';
import apiClient from '../../lib/api-client';
import type { MLModelInfo, MLBiasReport, SurvivalCurveResponse, Assessment } from '../../lib/types';

export default function IntelligencePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modelInfo, setModelInfo] = useState<MLModelInfo | null>(null);
  const [biasReport, setBiasReport] = useState<MLBiasReport | null>(null);
  const [survivalCurve, setSurvivalCurve] = useState<SurvivalCurveResponse | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [model, bias, survival, assessmentList] = await Promise.all([
        apiClient.getMLModelInfo().catch(() => null),
        apiClient.getMLBiasReport().catch(() => null),
        apiClient.getSurvivalCurve().catch(() => null),
        apiClient.getAssessments({ limit: 50 }).catch(() => []),
      ]);
      setModelInfo(model);
      setBiasReport(bias);
      setSurvivalCurve(survival);
      setAssessments(assessmentList);
    } catch (err: any) {
      setError(err.message || 'Failed to load intelligence data');
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    try {
      setTraining(true);
      setError(null);
      const res = await apiClient.trainMLModel({ algorithm: 'random_forest', min_samples: 5 });
      setTrainResult(res);
      await loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Training failed');
    } finally {
      setTraining(false);
    }
  };

  const handleClusterAll = async () => {
    try {
      setError(null);
      const res = await apiClient.clusterTenant();
      setTrainResult({ status: 'clustered', clusters: res.clusters_found || 0, threats: res.quality?.n_threats || 0 });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Clustering failed');
    }
  };

  if (loading) return <LoadingPage />;

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Risk Intelligence</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">ML models, threat intelligence, and analytics across all assessments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={handleClusterAll}>
            <Boxes className="w-4 h-4 mr-2" />
            Cluster All Threats
          </Button>
          <Button onClick={handleTrain} disabled={training}>
            {training ? (
              <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Training...</>
            ) : (
              <><Brain className="w-4 h-4 mr-2" />Train ML Model</>
            )}
          </Button>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {trainResult && (
        <div className="p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-xl mb-6">
          <p className="text-sm font-semibold text-green-800 dark:text-green-300">
            {trainResult.status === 'clustered'
              ? `Clustering complete: ${trainResult.clusters} clusters from ${trainResult.threats} threats`
              : `Training complete: ${trainResult.algorithm || 'ML'} model with ${trainResult.samples || 0} samples`}
          </p>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={Brain}
          iconColor="text-purple-600"
          iconBg="bg-purple-100"
          title="ML Model"
          value={modelInfo?.trained ? 'Trained' : 'Not Trained'}
          subtitle={modelInfo?.algorithm || 'N/A'}
          valueColor={modelInfo?.trained ? 'text-green-600' : 'text-amber-600'}
        />
        <StatCard
          icon={TrendingUp}
          iconColor="text-blue-600"
          iconBg="bg-blue-100"
          title="Features"
          value={String(modelInfo?.feature_count || 0)}
          subtitle="Input dimensions"
        />
        <StatCard
          icon={BarChart3}
          iconColor="text-emerald-600"
          iconBg="bg-emerald-100"
          title="Accuracy"
          value={modelInfo?.metrics?.accuracy ? `${(modelInfo.metrics.accuracy * 100).toFixed(1)}%` : 'N/A'}
          subtitle={modelInfo?.training_samples ? `${modelInfo.training_samples} samples` : 'No data'}
        />
        <StatCard
          icon={Activity}
          iconColor="text-indigo-600"
          iconBg="bg-indigo-100"
          title="Median Risk Persistence"
          value={survivalCurve?.median_survival_days ? `${survivalCurve.median_survival_days}d` : 'N/A'}
          subtitle="Time risks remain open"
        />
      </div>

      {/* Bias Monitoring Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-amber-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Bias Monitoring</h2>
          <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">Score distribution across sectors</span>
        </div>
        {biasReport && biasReport.sectors && Object.keys(biasReport.sectors).length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 px-3 text-gray-600 dark:text-gray-400 font-medium">Sector</th>
                  <th className="text-right py-2 px-3 text-gray-600 dark:text-gray-400 font-medium">Threats</th>
                  <th className="text-right py-2 px-3 text-gray-600 dark:text-gray-400 font-medium">Mean Score</th>
                  <th className="text-right py-2 px-3 text-gray-600 dark:text-gray-400 font-medium">Std Dev</th>
                  <th className="text-left py-2 px-3 text-gray-600 dark:text-gray-400 font-medium">Distribution</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(biasReport.sectors).map(([sectorName, s]) => (
                  <tr key={sectorName} className="border-b border-gray-50 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="py-2 px-3 font-medium text-gray-900 dark:text-white capitalize">{sectorName}</td>
                    <td className="py-2 px-3 text-right text-gray-700 dark:text-gray-300">{s.count}</td>
                    <td className="py-2 px-3 text-right font-bold text-gray-900 dark:text-white">{s.mean.toFixed(1)}</td>
                    <td className="py-2 px-3 text-right text-gray-600 dark:text-gray-400">{s.std.toFixed(2)}</td>
                    <td className="py-2 px-3">
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            s.mean >= 70 ? 'bg-red-500' : s.mean >= 50 ? 'bg-amber-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${Math.min(s.mean, 100)}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No bias data available. Train the model and score threats to generate reports.
          </p>
        )}
      </div>

      {/* Survival Analysis */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Survival Analysis</h2>
          <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">Risk persistence over time</span>
        </div>
        {survivalCurve && survivalCurve.timeline_days && survivalCurve.timeline_days.length > 0 ? (
          <div>
            <div className="flex items-end gap-1 h-32 bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
              {survivalCurve.timeline_days.map((day, i) => (
                <div
                  key={i}
                  className="flex-1 bg-indigo-400 hover:bg-indigo-500 rounded-t transition-colors cursor-pointer"
                  style={{ height: `${(survivalCurve.survival_probability[i] || 0) * 100}%` }}
                  title={`Day ${day}: ${((survivalCurve.survival_probability[i] || 0) * 100).toFixed(1)}% probability`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-gray-400 dark:text-gray-500 mt-1 px-4">
              <span>Day 0</span>
              {survivalCurve.median_survival_days && <span>Median: Day {survivalCurve.median_survival_days}</span>}
              <span>Day {survivalCurve.timeline_days[survivalCurve.timeline_days.length - 1]}</span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No survival data available. Active risks need history data for analysis.
          </p>
        )}
      </div>

      {/* Assessments Quick Access */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Assessment Intelligence</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          View enrichment, scoring, graph, and clustering for each assessment.
        </p>
        {assessments.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No assessments found.</p>
        ) : (
          <div className="space-y-2">
            {assessments.map((a) => (
              <a
                key={a.id}
                href={`/assessments/${a.id}`}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/40 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition group"
              >
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{a.title}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{a.status} / {a.overall_impact} impact</p>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  iconColor,
  iconBg,
  title,
  value,
  subtitle,
  valueColor,
}: {
  icon: any;
  iconColor: string;
  iconBg: string;
  title: string;
  value: string;
  subtitle: string;
  valueColor?: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg ${iconBg}`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <span className="text-sm text-gray-600 dark:text-gray-400">{title}</span>
      </div>
      <p className={`text-2xl font-bold ${valueColor || 'text-gray-900 dark:text-white'}`}>{value}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
    </div>
  );
}
