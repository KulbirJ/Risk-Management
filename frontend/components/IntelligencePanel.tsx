'use client';

import { useState, useEffect } from 'react';
import {
  Brain,
  Zap,
  AlertTriangle,
  Shield,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Clock,
} from 'lucide-react';
import { Button } from './Button';
import { SeverityBadge } from './Badge';
import { Alert } from './Alert';
import apiClient from '../lib/api-client';
import type {
  IntelligenceEnrichResponse,
  IntelligenceJob,
  Threat,
  ActiveRisk,
  Recommendation,
} from '../lib/types';

interface IntelligencePanelProps {
  assessmentId: string;
  onEnrichComplete: () => void; // callback to reload assessment data
}

export function IntelligencePanel({ assessmentId, onEnrichComplete }: IntelligencePanelProps) {
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<IntelligenceJob | null>(null);
  const [enrichResult, setEnrichResult] = useState<IntelligenceEnrichResponse | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [jobHistory, setJobHistory] = useState<IntelligenceJob[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    loadLastJob();
  }, [assessmentId]);

  const loadLastJob = async () => {
    try {
      const jobs = await apiClient.getIntelligenceJobs({
        assessment_id: assessmentId,
        limit: 1,
      });
      if (jobs.length > 0) {
        setLastJob(jobs[0]);
      }
    } catch {
      // Silently fail - intelligence may not be available
    }
  };

  const loadJobHistory = async () => {
    try {
      setLoadingHistory(true);
      const jobs = await apiClient.getIntelligenceJobs({
        assessment_id: assessmentId,
        limit: 10,
      });
      setJobHistory(jobs);
    } catch {
      // Silently fail
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleEnrich = async () => {
    try {
      setEnriching(true);
      setError(null);
      setSuccess(null);
      setEnrichResult(null);

      const result = await apiClient.enrichAssessment(assessmentId);
      setEnrichResult(result);

      if (result.status === 'completed') {
        setSuccess(
          `AI analysis complete: ${result.threats_mapped} threats, ${result.risks_created} risks, ${result.recommendations_generated} recommendations identified.`
        );
        onEnrichComplete();
      } else if (result.status === 'failed') {
        setError(`Enrichment failed: ${result.errors?.join(', ') || 'Unknown error'}`);
      }

      // Refresh last job
      await loadLastJob();
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail || 'Failed to start AI enrichment';
      
      // If 409 conflict (stuck job), auto-reset and retry once
      if (status === 409) {
        try {
          await apiClient.resetIntelligenceJobs(assessmentId);
          const retryResult = await apiClient.enrichAssessment(assessmentId);
          setEnrichResult(retryResult);
          if (retryResult.status === 'completed') {
            setSuccess(
              `AI analysis complete: ${retryResult.threats_mapped} threats, ${retryResult.risks_created} risks, ${retryResult.recommendations_generated} recommendations identified.`
            );
            onEnrichComplete();
          } else if (retryResult.status === 'failed') {
            setError(`Enrichment failed: ${retryResult.errors?.join(', ') || 'Unknown error'}`);
          }
          await loadLastJob();
          return;
        } catch (retryErr: any) {
          setError(retryErr.response?.data?.detail || 'Failed after auto-reset. Try again.');
        }
      } else {
        setError(detail);
      }
    } finally {
      setEnriching(false);
    }
  };

  const handleReset = async () => {
    try {
      await apiClient.resetIntelligenceJobs(assessmentId);
      setLastJob(null);
      setEnrichResult(null);
      setError(null);
      setSuccess('Stuck jobs cleared. You can now re-run enrichment.');
      await loadLastJob();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset jobs');
    }
  };

  const toggleHistory = async () => {
    if (!showHistory) {
      await loadJobHistory();
    }
    setShowHistory(!showHistory);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'running':
      case 'pending':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-700 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-700 bg-red-50 border-red-200';
      case 'running':
      case 'pending':
        return 'text-blue-700 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <Brain className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">AI Intelligence</h3>
            <p className="text-sm text-gray-600">
              Powered by Amazon Bedrock (Nova Pro)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {lastJob && lastJob.status !== 'running' && lastJob.status !== 'pending' && (
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          )}
          <Button
            size="sm"
            onClick={handleEnrich}
            disabled={enriching}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {enriching ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 mr-2" />
                AI Enrich
              </>
            )}
          </Button>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess(null)} />}

      {/* Enrichment Results Summary */}
      {enrichResult && enrichResult.status === 'completed' && (
        <div className="grid grid-cols-4 gap-3 mt-4">
          <ResultCard
            icon={<Zap className="w-5 h-5 text-yellow-600" />}
            label="Vulnerabilities"
            value={enrichResult.vulnerabilities_identified}
            color="yellow"
          />
          <ResultCard
            icon={<AlertTriangle className="w-5 h-5 text-orange-600" />}
            label="Threats"
            value={enrichResult.threats_mapped}
            color="orange"
          />
          <ResultCard
            icon={<Shield className="w-5 h-5 text-red-600" />}
            label="Active Risks"
            value={enrichResult.risks_created}
            color="red"
          />
          <ResultCard
            icon={<Lightbulb className="w-5 h-5 text-green-600" />}
            label="Recommendations"
            value={enrichResult.recommendations_generated}
            color="green"
          />
        </div>
      )}

      {/* Last Job Info */}
      {lastJob && !enrichResult && (
        <div className={`mt-4 flex items-center gap-3 px-3 py-2 rounded-md border ${getStatusColor(lastJob.status)}`}>
          {getStatusIcon(lastJob.status)}
          <span className="text-sm font-medium">
            Last run: {lastJob.status}
            {lastJob.completed_at && (
              <span className="text-xs ml-2 opacity-75">
                {new Date(lastJob.completed_at).toLocaleString()}
              </span>
            )}
          </span>
          {lastJob.results && (
            <span className="text-xs ml-auto">
              {lastJob.results.threats_mapped || 0} threats, {lastJob.results.risks_created || 0} risks, {lastJob.results.recommendations_generated || 0} recs
            </span>
          )}
        </div>
      )}

      {/* Job History Toggle */}
      <div className="mt-3">
        <button
          onClick={toggleHistory}
          className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
        >
          {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {showHistory ? 'Hide' : 'Show'} enrichment history
        </button>

        {showHistory && (
          <div className="mt-3 space-y-2">
            {loadingHistory ? (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading...
              </div>
            ) : jobHistory.length === 0 ? (
              <p className="text-sm text-gray-500">No enrichment jobs found.</p>
            ) : (
              jobHistory.map((job) => (
                <div
                  key={job.id}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md border text-sm ${getStatusColor(job.status)}`}
                >
                  {getStatusIcon(job.status)}
                  <span className="font-medium capitalize">{job.status}</span>
                  <span className="text-xs opacity-75">
                    {new Date(job.created_at).toLocaleString()}
                  </span>
                  {job.model_id && (
                    <span className="text-xs ml-auto opacity-60">{job.model_id}</span>
                  )}
                  {job.error_message && (
                    <span className="text-xs text-red-600 ml-2 truncate max-w-[200px]" title={job.error_message}>
                      {job.error_message}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ResultCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  const bgColors: Record<string, string> = {
    yellow: 'bg-yellow-50 border-yellow-200',
    orange: 'bg-orange-50 border-orange-200',
    red: 'bg-red-50 border-red-200',
    green: 'bg-green-50 border-green-200',
  };

  return (
    <div className={`rounded-lg border p-3 text-center ${bgColors[color] || 'bg-gray-50 border-gray-200'}`}>
      <div className="flex justify-center mb-1">{icon}</div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-600">{label}</p>
    </div>
  );
}

// Badge component for AI-generated items
export function AiBadge() {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 border border-indigo-200">
      <Sparkles className="w-3 h-3" />
      AI
    </span>
  );
}
