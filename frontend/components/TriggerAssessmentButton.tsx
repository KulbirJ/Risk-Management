'use client';

import { useEffect, useRef, useState } from 'react';
import { CheckCircle, Clock, Loader2, X, XCircle, Zap } from 'lucide-react';
import apiClient from '../lib/api-client';
import type { FullRunStep, FullRunResults, IntelligenceJob } from '../lib/types';

// ─────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────

interface TriggerAssessmentButtonProps {
  assessmentId: string;
  /** Called after a successful run — use to reload assessment data. */
  onComplete?: () => void;
}

// ─────────────────────────────────────────────────────────────────
// Step icon helper
// ─────────────────────────────────────────────────────────────────

function StepIcon({ status }: { status: FullRunStep['status'] }) {
  switch (status) {
    case 'running':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />;
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />;
    default:
      return <Clock className="w-4 h-4 text-gray-300 flex-shrink-0" />;
  }
}

// ─────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────

export function TriggerAssessmentButton({ assessmentId, onComplete }: TriggerAssessmentButtonProps) {
  const [isOpen, setIsOpen]         = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  const [jobId, setJobId]           = useState<string | null>(null);
  const [job, setJob]               = useState<IntelligenceJob | null>(null);
  const [error, setError]           = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const results: FullRunResults | null = (job?.results as FullRunResults) ?? null;
  const percent  = results?.percent_complete ?? 0;
  const steps: FullRunStep[] = results?.steps ?? [];
  const isDone   = job?.status === 'completed' || job?.status === 'failed';

  // Detect a job stuck in pending/running for >2 minutes.
  // Use created_at as fallback because started_at is NULL while status="pending".
  const jobAgeMs = job
    ? Date.now() - new Date(job.started_at ?? job.created_at).getTime()
    : 0;
  const isStuck = !isDone && !!job && jobAgeMs > 2 * 60 * 1000;

  // ── On mount: reconnect to any in-progress job ───────────────────
  // If the user refreshed the page mid-run, pick up where we left off.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const jobs = await apiClient.getIntelligenceJobs({
          assessment_id: assessmentId,
          limit: 1,
        });
        if (cancelled) return;
        const latest = jobs[0];
        if (latest && (latest.status === 'running' || latest.status === 'pending')) {
          setJob(latest);
          setJobId(latest.id);
          // Don't auto-open the modal on reconnect — just resume polling silently
        }
      } catch {
        // Non-critical: if this fails, user can still trigger manually
      }
    })();
    return () => { cancelled = true; };
  }, [assessmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Polling ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId) return;

    pollRef.current = setInterval(async () => {
      try {
        const updated = await apiClient.getIntelligenceJob(jobId);
        setJob(updated);
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          if (updated.status === 'completed') {
            // Give user a moment to read the summary, then refresh parent data
            setTimeout(() => { onComplete?.(); }, 1800);
          }
        }
      } catch {
        // Ignore transient poll errors
      }
    }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Force-reset stuck job ────────────────────────────────────────
  const handleForceReset = async () => {
    setIsResetting(true);
    try {
      await apiClient.resetIntelligenceJobs(assessmentId);
      // Clear local state so the user can trigger a fresh run
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      setJob(null);
      setJobId(null);
      setError(null);
      setIsOpen(false);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Reset failed — try again.');
    } finally {
      setIsResetting(false);
    }
  };

  // ── Trigger ──────────────────────────────────────────────────────
  const handleTrigger = async () => {
    // Reset state from any previous run
    setIsLaunching(true);
    setError(null);
    setJob(null);
    setJobId(null);
    try {
      const resp = await apiClient.runFullAssessment(assessmentId);
      setJobId(resp.job_id);
      setIsOpen(true);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ??
        err.message ??
        'Failed to start the full assessment pipeline.';
      setError(msg);
      setIsOpen(true);
    } finally {
      setIsLaunching(false);
    }
  };

  const handleClose = () => {
    if (!isDone && jobId && !isStuck) return; // block close while actively running (allow if stuck)
    setIsOpen(false);
  };

  // ── Progress bar colour ──────────────────────────────────────────
  const barColour =
    job?.status === 'completed' ? 'bg-green-500' :
    job?.status === 'failed'    ? 'bg-red-400'   :
    'bg-blue-500';

  // ── Render ───────────────────────────────────────────────────────
  return (
    <>
      {/* ── Trigger button / stuck indicator ── */}
      <div className="inline-flex items-center gap-2">
        <button
          onClick={handleTrigger}
          disabled={isLaunching || (!isDone && !!jobId && !isStuck)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 text-white
                     text-sm font-semibold shadow-md hover:bg-indigo-700 active:bg-indigo-800
                     disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {isLaunching
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <Zap className="w-4 h-4" />}
          {isLaunching ? 'Starting…' : 'Trigger Assessment'}
        </button>

        {/* Running/pending badge — always visible while a job is active */}
        {!isDone && !!jobId && (
          <span
            className={`inline-flex items-center gap-1.5 text-xs rounded-lg px-3 py-2 border ${
              isStuck
                ? 'text-amber-700 bg-amber-50 border-amber-200'
                : 'text-blue-700 bg-blue-50 border-blue-200'
            }`}
          >
            <Loader2 className={`w-3.5 h-3.5 animate-spin ${
              isStuck ? 'text-amber-500' : 'text-blue-500'
            }`} />
            {isStuck ? 'Stuck — ' : 'Running — '}
            <button
              onClick={isStuck ? handleForceReset : () => setIsOpen(true)}
              disabled={isResetting}
              className="font-semibold underline hover:opacity-80 disabled:opacity-50"
              title={isStuck ? 'Reset the stuck job so you can trigger a fresh run' : 'View progress'}
            >
              {isResetting ? 'Resetting…' : isStuck ? 'Force Reset' : 'View progress'}
            </button>
          </span>
        )}
      </div>

      {/* ── Modal ── */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Full Assessment Run Progress"
        >
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">

            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100">
                  <Zap className="h-5 w-5 text-indigo-600" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900 leading-tight">
                    Full Assessment Run
                  </h2>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {isDone
                      ? job?.status === 'completed'
                        ? 'All steps completed — reloading results…'
                        : 'Finished with some errors (completed steps were saved)'
                      : isStuck
                      ? `Appears stuck (${Math.floor(jobAgeMs / 60000)} min) — force-reset below`
                      : jobId
                      ? 'Pipeline is running — please wait…'
                      : 'Starting pipeline…'}
                  </p>
                </div>
              </div>

              <button
                onClick={handleClose}
                disabled={!isDone && !!jobId && !isStuck}
                className="p-1.5 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100
                           disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title={!isDone && !!jobId && !isStuck ? 'Cannot close while running' : 'Close'}
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Error before job created */}
            {error && !jobId && (
              <div className="mx-6 mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                <strong>Error:</strong> {error}
              </div>
            )}

            {/* Overall progress bar */}
            {jobId && (
              <div className="px-6 pt-4 pb-2">
                <div className="flex justify-between items-center text-xs text-gray-500 mb-1.5">
                  <span className="font-medium">Overall progress</span>
                  <span className="tabular-nums font-semibold text-gray-700">{percent}%</span>
                </div>
                <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ease-out ${barColour}`}
                    style={{ width: `${Math.max(percent, percent > 0 ? 3 : 0)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Steps list */}
            {steps.length > 0 && (
              <ul className="mx-6 my-3 rounded-xl border border-gray-100 divide-y divide-gray-100 overflow-hidden text-sm">
                {steps.map((step, idx) => (
                  <li
                    key={step.name}
                    className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                      step.status === 'running' ? 'bg-blue-50' : 'bg-white'
                    }`}
                  >
                    <StepIcon status={step.status} />

                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-1.5">
                        <span className={`font-medium ${step.status === 'running' ? 'text-blue-700' : 'text-gray-800'}`}>
                          {step.label}
                        </span>
                        <span className="text-[10px] text-gray-400 font-medium">
                          {idx + 1}/{steps.length}
                        </span>
                      </div>
                      {step.message && (
                        <p className={`mt-0.5 text-xs truncate ${
                          step.status === 'failed' ? 'text-red-500' : 'text-gray-500'
                        }`}>
                          {step.message}
                        </p>
                      )}
                    </div>

                    {/* Status badge */}
                    <span className={`ml-2 flex-shrink-0 text-[10px] font-bold uppercase tracking-wide
                                      px-2 py-0.5 rounded-full ${
                      step.status === 'completed' ? 'bg-green-100 text-green-700' :
                      step.status === 'running'   ? 'bg-blue-100  text-blue-700'  :
                      step.status === 'failed'    ? 'bg-red-100   text-red-600'   :
                                                    'bg-gray-100  text-gray-400'
                    }`}>
                      {step.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {/* Pending — steps not loaded yet */}
            {jobId && steps.length === 0 && !error && (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                Initialising pipeline…
              </div>
            )}

            {/* Footer */}
            <div className="border-t border-gray-100 px-6 py-3 flex items-center justify-between bg-gray-50 rounded-b-2xl">
              <p className="text-xs">
                {job?.status === 'completed' && (
                  <span className="text-green-600 font-medium flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" />
                    All steps finished. Refreshing assessment data…
                  </span>
                )}
                {job?.status === 'failed' && (
                  <span className="text-red-500 flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5" />
                    Some steps encountered errors — completed steps were saved.
                  </span>
                )}
                {!isDone && jobId && (
                  <span className="text-gray-400 italic">
                    {isStuck ? 'Job appears stuck — use Reset to start fresh.' : 'AI and ML steps may take a few minutes…'}
                  </span>
                )}
              </p>

              <div className="ml-4 flex items-center gap-2">
                {!isDone && !!jobId && (
                  <button
                    onClick={handleForceReset}
                    disabled={isResetting}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors disabled:opacity-50 ${
                      isStuck
                        ? 'text-amber-700 bg-amber-50 border-amber-200 hover:bg-amber-100'
                        : 'text-gray-600 bg-white border-gray-200 hover:bg-gray-100'
                    }`}
                    title="Reset this job so you can trigger a fresh run"
                  >
                    {isResetting ? 'Resetting…' : 'Reset Job'}
                  </button>
                )}
                <button
                  onClick={handleClose}
                  disabled={!isDone && !!jobId && !isStuck}
                  className="px-4 py-1.5 rounded-lg text-sm font-medium text-gray-600
                             hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  {isDone ? 'Close' : isStuck ? 'Close' : 'Running…'}
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </>
  );
}
