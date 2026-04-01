'use client';

import { useEffect } from 'react';
import { Loader2, Zap } from 'lucide-react';
import { usePipeline, usePipelineReconnect } from './PipelineContext';
import { PipelineProgressBar } from './PipelineProgressBar';
import type { FullRunResults } from '../lib/types';

// ─────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────

interface TriggerAssessmentButtonProps {
  assessmentId: string;
  assessmentTitle?: string;
  /** Called after a successful run — use to reload assessment data. */
  onComplete?: () => void;
}

// ─────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────

export function TriggerAssessmentButton({
  assessmentId,
  assessmentTitle,
  onComplete,
}: TriggerAssessmentButtonProps) {
  const { pipelines, triggerPipeline, resetPipeline, dismissPipeline, getPipeline } = usePipeline();
  const reconnect = usePipelineReconnect();

  const pipeline = getPipeline(assessmentId);
  const job = pipeline?.job ?? null;
  const isDone = job?.status === 'completed' || job?.status === 'failed';
  const isActive = !!pipeline && !isDone && !!pipeline.jobId;
  const isLaunching = !!pipeline && !pipeline.jobId && !pipeline.error;

  // ── On mount: reconnect to any in-progress job ───────────────────
  useEffect(() => {
    reconnect(assessmentId, assessmentTitle);
  }, [assessmentId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-refresh parent when completed ──────────────────────────
  useEffect(() => {
    if (job?.status === 'completed') {
      const t = setTimeout(() => onComplete?.(), 1800);
      return () => clearTimeout(t);
    }
  }, [job?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Handlers ────────────────────────────────────────────────────
  const handleTrigger = () => {
    triggerPipeline(assessmentId, assessmentTitle);
  };

  const handleReset = () => {
    resetPipeline(assessmentId);
  };

  const handleDismiss = () => {
    dismissPipeline(assessmentId);
  };

  // ── Render ───────────────────────────────────────────────────────
  return (
    <div className="space-y-3">
      {/* ── Trigger button ── */}
      <button
        onClick={handleTrigger}
        disabled={isLaunching || isActive}
        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 text-white
                   text-sm font-semibold shadow-md hover:bg-indigo-700 active:bg-indigo-800
                   disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
      >
        {isLaunching
          ? <Loader2 className="w-4 h-4 animate-spin" />
          : <Zap className="w-4 h-4" />}
        {isLaunching ? 'Starting...' : isActive ? 'Pipeline Running' : 'Trigger Assessment'}
      </button>

      {/* ── Inline progress bar (non-blocking) ── */}
      {pipeline && (pipeline.jobId || pipeline.error) && (
        <PipelineProgressBar
          pipeline={pipeline}
          onReset={handleReset}
          onDismiss={handleDismiss}
          onComplete={onComplete}
        />
      )}
    </div>
  );
}
