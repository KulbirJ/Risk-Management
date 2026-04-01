'use client';

import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import apiClient from '../lib/api-client';
import type { IntelligenceJob, FullRunResults, FullRunStep } from '../lib/types';

// ─────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────

export interface PipelineState {
  jobId: string;
  assessmentId: string;
  assessmentTitle?: string;
  job: IntelligenceJob | null;
  error: string | null;
}

interface PipelineContextValue {
  /** All active/recent pipelines keyed by assessmentId */
  pipelines: Record<string, PipelineState>;
  /** Trigger a new pipeline run */
  triggerPipeline: (assessmentId: string, assessmentTitle?: string) => Promise<void>;
  /** Force-reset a stuck pipeline */
  resetPipeline: (assessmentId: string) => Promise<void>;
  /** Dismiss a completed/failed pipeline from the tracker */
  dismissPipeline: (assessmentId: string) => void;
  /** Get helpers for a specific assessment */
  getPipeline: (assessmentId: string) => PipelineState | null;
}

const PipelineContext = createContext<PipelineContextValue | null>(null);

export function usePipeline() {
  const ctx = useContext(PipelineContext);
  if (!ctx) throw new Error('usePipeline must be used inside <PipelineProvider>');
  return ctx;
}

// ─────────────────────────────────────────────────────────────────
// Provider
// ─────────────────────────────────────────────────────────────────

const POLL_INTERVAL = 3000;

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [pipelines, setPipelines] = useState<Record<string, PipelineState>>({});
  const pollRefs = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  // ── Start polling for a job ──────────────────────────────────────
  const startPolling = useCallback((assessmentId: string, jobId: string) => {
    // Clear existing interval if any
    if (pollRefs.current[assessmentId]) {
      clearInterval(pollRefs.current[assessmentId]);
    }

    pollRefs.current[assessmentId] = setInterval(async () => {
      try {
        const updated = await apiClient.getIntelligenceJob(jobId);
        setPipelines((prev) => ({
          ...prev,
          [assessmentId]: {
            ...prev[assessmentId],
            job: updated,
          },
        }));

        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(pollRefs.current[assessmentId]);
          delete pollRefs.current[assessmentId];
        }
      } catch {
        // Ignore transient errors
      }
    }, POLL_INTERVAL);
  }, []);

  // ── Trigger a pipeline ───────────────────────────────────────────
  const triggerPipeline = useCallback(
    async (assessmentId: string, assessmentTitle?: string) => {
      // Already running?
      const existing = pipelines[assessmentId];
      if (
        existing?.job &&
        existing.job.status !== 'completed' &&
        existing.job.status !== 'failed'
      ) {
        return; // Silently skip duplicate trigger
      }

      setPipelines((prev) => ({
        ...prev,
        [assessmentId]: {
          jobId: '',
          assessmentId,
          assessmentTitle,
          job: null,
          error: null,
        },
      }));

      try {
        const resp = await apiClient.runFullAssessment(assessmentId);
        setPipelines((prev) => ({
          ...prev,
          [assessmentId]: {
            ...prev[assessmentId],
            jobId: resp.job_id,
          },
        }));
        startPolling(assessmentId, resp.job_id);
      } catch (err: any) {
        const msg =
          err.response?.data?.detail ??
          err.message ??
          'Failed to start pipeline.';
        setPipelines((prev) => ({
          ...prev,
          [assessmentId]: {
            ...prev[assessmentId],
            error: msg,
          },
        }));
      }
    },
    [pipelines, startPolling],
  );

  // ── Reset a stuck pipeline ──────────────────────────────────────
  const resetPipeline = useCallback(
    async (assessmentId: string) => {
      try {
        await apiClient.resetIntelligenceJobs(assessmentId);
        if (pollRefs.current[assessmentId]) {
          clearInterval(pollRefs.current[assessmentId]);
          delete pollRefs.current[assessmentId];
        }
        setPipelines((prev) => {
          const next = { ...prev };
          delete next[assessmentId];
          return next;
        });
      } catch (err: any) {
        setPipelines((prev) => ({
          ...prev,
          [assessmentId]: {
            ...prev[assessmentId],
            error: err.response?.data?.detail ?? 'Reset failed.',
          },
        }));
      }
    },
    [],
  );

  // ── Dismiss (remove from UI) ────────────────────────────────────
  const dismissPipeline = useCallback((assessmentId: string) => {
    if (pollRefs.current[assessmentId]) {
      clearInterval(pollRefs.current[assessmentId]);
      delete pollRefs.current[assessmentId];
    }
    setPipelines((prev) => {
      const next = { ...prev };
      delete next[assessmentId];
      return next;
    });
  }, []);

  // ── Helper ──────────────────────────────────────────────────────
  const getPipeline = useCallback(
    (assessmentId: string) => pipelines[assessmentId] ?? null,
    [pipelines],
  );

  // ── Reconnect on mount: pick up any running jobs ────────────────
  useEffect(() => {
    // Intentionally empty — reconnection happens per-assessment in TriggerAssessmentButton
    return () => {
      // Cleanup all polls on unmount
      Object.values(pollRefs.current).forEach(clearInterval);
    };
  }, []);

  // ── Reconnect helper (called from assessment pages) ─────────────
  // Check once for running jobs on a given assessment
  const reconnect = useCallback(
    async (assessmentId: string, assessmentTitle?: string) => {
      // Skip if already tracked
      if (pipelines[assessmentId]?.jobId) return;
      try {
        const jobs = await apiClient.getIntelligenceJobs({
          assessment_id: assessmentId,
          limit: 1,
        });
        const latest = jobs[0];
        if (latest && (latest.status === 'running' || latest.status === 'pending')) {
          setPipelines((prev) => ({
            ...prev,
            [assessmentId]: {
              jobId: latest.id,
              assessmentId,
              assessmentTitle,
              job: latest,
              error: null,
            },
          }));
          startPolling(assessmentId, latest.id);
        }
      } catch {
        // Non-critical
      }
    },
    [pipelines, startPolling],
  );

  return (
    <PipelineContext.Provider
      value={{
        pipelines,
        triggerPipeline,
        resetPipeline,
        dismissPipeline,
        getPipeline,
        // @ts-ignore — we'll add reconnect to the interface via cast
        reconnect,
      }}
    >
      {children}
    </PipelineContext.Provider>
  );
}

/** Extra hook to access reconnect */
export function usePipelineReconnect() {
  const ctx = useContext(PipelineContext) as any;
  return ctx?.reconnect as (assessmentId: string, title?: string) => Promise<void>;
}
