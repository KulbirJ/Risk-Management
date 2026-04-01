'use client';

import { CheckCircle, Loader2, XCircle, Clock, RotateCcw, X } from 'lucide-react';
import type { FullRunStep, FullRunResults, IntelligenceJob } from '../lib/types';
import type { PipelineState } from './PipelineContext';

// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────

const STEP_COLOURS: Record<FullRunStep['status'], { pipe: string; node: string; text: string; ring: string }> = {
  completed: {
    pipe: 'bg-emerald-400',
    node: 'bg-emerald-500 border-emerald-300 shadow-emerald-200/60',
    text: 'text-emerald-700',
    ring: 'ring-emerald-400/30',
  },
  running: {
    pipe: 'bg-blue-400 animate-pulse',
    node: 'bg-blue-500 border-blue-300 shadow-blue-300/60',
    text: 'text-blue-700',
    ring: 'ring-blue-400/40',
  },
  failed: {
    pipe: 'bg-red-400',
    node: 'bg-red-500 border-red-300 shadow-red-200/60',
    text: 'text-red-600',
    ring: 'ring-red-400/30',
  },
  pending: {
    pipe: 'bg-gray-200 dark:bg-gray-700',
    node: 'bg-gray-300 dark:bg-gray-600 border-gray-200 dark:border-gray-500',
    text: 'text-gray-400 dark:text-gray-500',
    ring: '',
  },
};

function StepNodeIcon({ status }: { status: FullRunStep['status'] }) {
  switch (status) {
    case 'running':
      return <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />;
    case 'completed':
      return <CheckCircle className="w-3.5 h-3.5 text-white" />;
    case 'failed':
      return <XCircle className="w-3.5 h-3.5 text-white" />;
    default:
      return <Clock className="w-3 h-3 text-white/70" />;
  }
}

/** Short step labels for the pipe visualization */
const SHORT_LABELS: Record<string, string> = {
  ai_enrichment: 'AI Enrich',
  intel_threats: 'Intel',
  ml_scoring: 'ML Score',
  clustering: 'Cluster',
  attack_mapping: 'ATT&CK Map',
};

// ─────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────

interface PipelineProgressBarProps {
  pipeline: PipelineState;
  onReset?: () => void;
  onDismiss?: () => void;
  /** Callback when pipeline completes successfully */
  onComplete?: () => void;
  compact?: boolean;
}

export function PipelineProgressBar({
  pipeline,
  onReset,
  onDismiss,
  onComplete,
  compact = false,
}: PipelineProgressBarProps) {
  const { job, error } = pipeline;
  const results: FullRunResults | null = (job?.results as FullRunResults) ?? null;
  const percent = results?.percent_complete ?? 0;
  const steps: FullRunStep[] = results?.steps ?? [];
  const isDone = job?.status === 'completed' || job?.status === 'failed';
  const isCompleted = job?.status === 'completed';
  const isFailed = job?.status === 'failed';

  // Detect stuck (>2 min)
  const jobAgeMs = job
    ? Date.now() - new Date(job.started_at ?? job.created_at).getTime()
    : 0;
  const isStuck = !isDone && !!job && jobAgeMs > 2 * 60 * 1000;

  // ── Error before job created ────────────────────────────────────
  if (error && !pipeline.jobId) {
    return (
      <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-700 dark:text-red-400 flex items-center justify-between">
        <span><strong>Error:</strong> {error}</span>
        {onDismiss && (
          <button onClick={onDismiss} className="ml-3 p-1 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-lg transition-colors">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  // ── Nothing to show yet ─────────────────────────────────────────
  if (!pipeline.jobId && !error) return null;

  // ── Loading (job created but no steps yet) ──────────────────────
  if (steps.length === 0 && !isDone) {
    return (
      <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20 px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Initialising pipeline...</span>
        </div>
      </div>
    );
  }

  // ── Status message ──────────────────────────────────────────────
  const statusMsg = isCompleted
    ? 'Pipeline completed successfully'
    : isFailed
    ? 'Pipeline finished with errors (completed steps saved)'
    : isStuck
    ? `Pipeline appears stuck (${Math.floor(jobAgeMs / 60000)} min)`
    : `Pipeline running — ${percent}%`;

  const statusColour = isCompleted
    ? 'text-emerald-600 dark:text-emerald-400'
    : isFailed
    ? 'text-red-500 dark:text-red-400'
    : isStuck
    ? 'text-amber-600 dark:text-amber-400'
    : 'text-blue-600 dark:text-blue-400';

  const borderColour = isCompleted
    ? 'border-emerald-200 dark:border-emerald-800'
    : isFailed
    ? 'border-red-200 dark:border-red-800'
    : isStuck
    ? 'border-amber-200 dark:border-amber-800'
    : 'border-blue-200 dark:border-blue-800';

  const bgColour = isCompleted
    ? 'bg-emerald-50/50 dark:bg-emerald-950/20'
    : isFailed
    ? 'bg-red-50/50 dark:bg-red-950/20'
    : isStuck
    ? 'bg-amber-50/50 dark:bg-amber-950/20'
    : 'bg-blue-50/30 dark:bg-blue-950/10';

  return (
    <div className={`rounded-xl border ${borderColour} ${bgColour} overflow-hidden transition-colors duration-500`}>
      {/* ── Header row ── */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <div className="flex items-center gap-2 min-w-0">
          {!isDone && <Loader2 className="w-4 h-4 animate-spin text-blue-500 flex-shrink-0" />}
          {isCompleted && <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
          {isFailed && <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />}
          <span className={`text-sm font-semibold ${statusColour}`}>
            {statusMsg}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {(isStuck || !isDone) && onReset && (
            <button
              onClick={onReset}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                isStuck
                  ? 'text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40 border-amber-200 dark:border-amber-700 hover:bg-amber-200 dark:hover:bg-amber-900/60'
                  : 'text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
          {isDone && onDismiss && (
            <button
              onClick={() => {
                if (isCompleted) onComplete?.();
                onDismiss();
              }}
              className="p-1 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* ── The physical pipe ── */}
      <div className="px-4 pt-2 pb-4">
        <div className="relative flex items-center">
          {steps.map((step, idx) => {
            const colours = STEP_COLOURS[step.status];
            const isLast = idx === steps.length - 1;
            const label = SHORT_LABELS[step.name] ?? step.label;

            return (
              <div
                key={step.name}
                className="flex items-center flex-1 min-w-0"
              >
                {/* ── Node (pipe joint) ── */}
                <div className="relative flex flex-col items-center z-10" style={{ minWidth: '2.5rem' }}>
                  {/* Pipe joint / valve */}
                  <div
                    className={`
                      w-8 h-8 rounded-full border-2 flex items-center justify-center
                      shadow-md transition-all duration-500
                      ${colours.node}
                      ${step.status === 'running' ? `ring-4 ${colours.ring}` : ''}
                    `}
                  >
                    <StepNodeIcon status={step.status} />
                  </div>
                  {/* Label below */}
                  {!compact && (
                    <div className="mt-1.5 text-center w-20 -ml-2.5">
                      <span className={`block text-[10px] font-semibold leading-tight ${colours.text}`}>
                        {label}
                      </span>
                      {step.status === 'running' && step.message && (
                        <span className="block text-[9px] text-blue-500/80 dark:text-blue-400/70 mt-0.5 leading-tight truncate">
                          {step.message}
                        </span>
                      )}
                      {step.status === 'failed' && step.message && (
                        <span className="block text-[9px] text-red-400 mt-0.5 leading-tight truncate" title={step.message}>
                          Error
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* ── Pipe segment between nodes ── */}
                {!isLast && (
                  <div className="flex-1 mx-0.5 relative" style={{ minWidth: '1.5rem' }}>
                    {/* Pipe body */}
                    <div className="h-3 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden border border-gray-300 dark:border-gray-600 shadow-inner">
                      {/* Flow fill */}
                      <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${
                          step.status === 'completed'
                            ? 'bg-emerald-400 dark:bg-emerald-500'
                            : step.status === 'running'
                            ? 'bg-blue-400 dark:bg-blue-500'
                            : step.status === 'failed'
                            ? 'bg-red-400 dark:bg-red-500'
                            : ''
                        }`}
                        style={{
                          width:
                            step.status === 'completed'
                              ? '100%'
                              : step.status === 'running'
                              ? '60%'
                              : step.status === 'failed'
                              ? '100%'
                              : '0%',
                        }}
                      />
                    </div>
                    {/* Pipe edge highlights for 3D effect */}
                    <div className="absolute inset-x-0 top-0 h-[3px] rounded-full bg-white/20 pointer-events-none" />
                    <div className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-black/5 dark:bg-black/20 pointer-events-none" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Pipe "flow" percentage ── */}
        <div className="mt-1 flex items-center justify-between">
          <span className="text-[10px] text-gray-400 dark:text-gray-500 font-medium">
            {steps.filter((s) => s.status === 'completed').length}/{steps.length} steps
          </span>
          <span className={`text-xs font-bold tabular-nums ${statusColour}`}>
            {percent}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Compact sidebar/nav indicator  (for Layout use)
// ─────────────────────────────────────────────────────────────────

interface PipelineNavIndicatorProps {
  pipelines: Record<string, PipelineState>;
}

export function PipelineNavIndicator({ pipelines }: PipelineNavIndicatorProps) {
  const active = Object.values(pipelines).filter(
    (p) => p.job && p.job.status !== 'completed' && p.job.status !== 'failed',
  );
  const completed = Object.values(pipelines).filter(
    (p) => p.job?.status === 'completed',
  );
  const failed = Object.values(pipelines).filter(
    (p) => p.job?.status === 'failed',
  );

  if (active.length === 0 && completed.length === 0 && failed.length === 0) return null;

  return (
    <div className="mx-3 my-2 space-y-1.5">
      {active.map((p) => {
        const results: FullRunResults | null = (p.job?.results as FullRunResults) ?? null;
        const pct = results?.percent_complete ?? 0;
        return (
          <div
            key={p.assessmentId}
            className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 px-3 py-2"
          >
            <div className="flex items-center gap-1.5 mb-1">
              <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
              <span className="text-[11px] font-semibold text-blue-700 dark:text-blue-300 truncate">
                {p.assessmentTitle || 'Assessment'}
              </span>
            </div>
            {/* Mini pipe */}
            <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-400 transition-all duration-700"
                style={{ width: `${Math.max(pct, pct > 0 ? 4 : 0)}%` }}
              />
            </div>
            <span className="text-[10px] text-blue-500 dark:text-blue-400 font-medium tabular-nums mt-0.5 block">
              {pct}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
