'use client';

import { useState, useEffect } from 'react';
import { Brain, BarChart3, RefreshCw, TrendingUp, AlertTriangle, ChevronDown, ChevronRight, Cpu, Info, Target, Activity } from 'lucide-react';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';
import apiClient from '../lib/api-client';
import type { MLModelInfo, MLTrainResponse, MLBatchScoreResponse, MLExplanation, MLBiasReport, SurvivalCurveResponse } from '../lib/types';

interface MLScoringPanelProps {
  assessmentId: string;
  onScoreComplete?: () => void;
}

export function MLScoringPanel({ assessmentId, onScoreComplete }: MLScoringPanelProps) {
  const [modelInfo, setModelInfo] = useState<MLModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [trainResult, setTrainResult] = useState<MLTrainResponse | null>(null);
  const [scoreResult, setScoreResult] = useState<MLBatchScoreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBias, setShowBias] = useState(false);
  const [biasReport, setBiasReport] = useState<MLBiasReport | null>(null);
  const [loadingBias, setLoadingBias] = useState(false);
  const [showSurvival, setShowSurvival] = useState(false);
  const [survivalCurve, setSurvivalCurve] = useState<SurvivalCurveResponse | null>(null);
  const [loadingSurvival, setLoadingSurvival] = useState(false);

  useEffect(() => {
    loadModelInfo();
  }, []);

  const loadModelInfo = async () => {
    try {
      setLoading(true);
      const info = await apiClient.getMLModelInfo();
      setModelInfo(info);
    } catch {
      // ML not available
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
      await loadModelInfo();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Training failed');
    } finally {
      setTraining(false);
    }
  };

  const handleScore = async () => {
    try {
      setScoring(true);
      setError(null);
      const res = await apiClient.scoreThreats({ assessment_id: assessmentId, persist: true });
      setScoreResult(res);
      onScoreComplete?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Scoring failed');
    } finally {
      setScoring(false);
    }
  };

  const loadBiasReport = async () => {
    try {
      setLoadingBias(true);
      const report = await apiClient.getMLBiasReport();
      setBiasReport(report);
    } catch {
      setBiasReport(null);
    } finally {
      setLoadingBias(false);
    }
  };

  const loadSurvivalCurve = async () => {
    try {
      setLoadingSurvival(true);
      const curve = await apiClient.getSurvivalCurve();
      setSurvivalCurve(curve);
    } catch {
      setSurvivalCurve(null);
    } finally {
      setLoadingSurvival(false);
    }
  };

  useEffect(() => {
    if (showBias) loadBiasReport();
  }, [showBias]);

  useEffect(() => {
    if (showSurvival) loadSurvivalCurve();
  }, [showSurvival]);

  if (loading) {
    return (
      <div className="bg-card rounded-lg border border-border p-6 mb-6 flex justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg border border-border p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
            <Brain className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">ML Risk Scoring</h3>
            <p className="text-sm text-muted-foreground">Machine learning-powered threat prioritization</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={handleTrain} disabled={training}>
            {training ? (
              <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Training...</>
            ) : (
              <><Cpu className="w-4 h-4 mr-2" />Train Model</>
            )}
          </Button>
          <Button size="sm" onClick={handleScore} disabled={scoring}>
            {scoring ? (
              <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Scoring...</>
            ) : (
              <><Target className="w-4 h-4 mr-2" />Score Threats</>
            )}
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 rounded-lg text-sm text-red-700 dark:text-red-400 mb-4">
          {error}
        </div>
      )}

      {/* Model Status */}
      {modelInfo && (
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="p-3 bg-muted rounded-lg text-center">
            <p className="text-xs text-muted-foreground mb-1">Model Status</p>
            <p className={`text-sm font-bold ${modelInfo.trained ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
              {modelInfo.trained ? 'Trained' : 'Not Trained'}
            </p>
          </div>
          <div className="p-3 bg-muted rounded-lg text-center">
            <p className="text-xs text-muted-foreground mb-1">Features</p>
            <p className="text-sm font-bold text-foreground">{modelInfo.feature_count}</p>
          </div>
          <div className="p-3 bg-muted rounded-lg text-center">
            <p className="text-xs text-muted-foreground mb-1">Algorithm</p>
            <p className="text-sm font-bold text-foreground">{modelInfo.algorithm || 'N/A'}</p>
          </div>
          <div className="p-3 bg-muted rounded-lg text-center">
            <p className="text-xs text-muted-foreground mb-1">Samples</p>
            <p className="text-sm font-bold text-foreground">
              {modelInfo.training_samples || 'N/A'}
            </p>
          </div>
        </div>
      )}

      {/* Train Result */}
      {trainResult && (
        <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800/40 rounded-lg mb-4">
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <span className="text-sm font-semibold text-purple-800 dark:text-purple-300">Training Complete</span>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-purple-600 dark:text-purple-400">Algorithm:</span>
              <span className="ml-2 font-bold text-foreground">{trainResult.algorithm}</span>
            </div>
            <div>
              <span className="text-purple-600 dark:text-purple-400">Samples:</span>
              <span className="ml-2 font-bold text-foreground">{trainResult.samples}</span>
            </div>
            <div>
              <span className="text-purple-600 dark:text-purple-400">Accuracy:</span>
              <span className="ml-2 font-bold text-foreground">
                {trainResult.accuracy ? `${(trainResult.accuracy * 100).toFixed(1)}%` : 'N/A'}
              </span>
            </div>
          </div>
          {trainResult.feature_importances && Object.keys(trainResult.feature_importances).length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-purple-700 dark:text-purple-400 mb-1">Top Feature Importances:</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(trainResult.feature_importances)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 8)
                  .map(([feature, importance]) => (
                    <span key={feature} className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 px-2 py-0.5 rounded-full">
                      {feature}: {(importance * 100).toFixed(1)}%
                    </span>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Score Results */}
      {scoreResult && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/40 rounded-lg mb-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-green-600 dark:text-green-400" />
            <span className="text-sm font-semibold text-green-800 dark:text-green-300">
              Scored {scoreResult.scored} Threat{scoreResult.scored !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {scoreResult.results.map((r) => (
              <div key={r.threat_id} className="flex items-center justify-between p-2 bg-card rounded border border-green-100 dark:border-green-800/30">
                <span className="text-sm text-muted-foreground truncate flex-1">{r.threat_id.slice(0, 8)}...</span>
                <div className="flex items-center gap-3">
                  <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        r.score >= 80 ? 'bg-red-500' : r.score >= 60 ? 'bg-amber-500' : r.score >= 40 ? 'bg-yellow-400' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(r.score, 100)}%` }}
                    />
                  </div>
                  <span className={`text-sm font-bold min-w-[3rem] text-right ${
                    r.score >= 80 ? 'text-red-600' : r.score >= 60 ? 'text-amber-600' : r.score >= 40 ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {r.score.toFixed(1)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expandable sections */}
      <div className="border-t border-border pt-4 space-y-3">
        {/* Bias Report */}
        <button
          onClick={() => setShowBias(!showBias)}
          className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary"
        >
          {showBias ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Bias Monitoring Report
        </button>
        {showBias && (
          <div className="ml-6">
            {loadingBias ? (
              <LoadingSpinner />
            ) : biasReport ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  {biasReport.total_threats} threats scored across {Object.keys(biasReport.sectors).length} sector{Object.keys(biasReport.sectors).length !== 1 ? 's' : ''}
                </p>
                {Object.keys(biasReport.sectors).length > 0 && (
                  <div className="space-y-1">
                    {Object.entries(biasReport.sectors).map(([sectorName, s]) => (
                      <div key={sectorName} className="flex items-center justify-between p-2 bg-muted rounded text-sm">
                        <span className="font-medium capitalize text-foreground">{sectorName}</span>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span>n={s.count}</span>
                          <span>mean={s.mean.toFixed(1)}</span>
                          <span>std={s.std.toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No bias data available yet. Score some threats first.</p>
            )}
          </div>
        )}

        {/* Survival Curve */}
        <button
          onClick={() => setShowSurvival(!showSurvival)}
          className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary"
        >
          {showSurvival ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <Activity className="w-4 h-4 text-indigo-500" />
          Survival Analysis
        </button>
        {showSurvival && (
          <div className="ml-6">
            {loadingSurvival ? (
              <LoadingSpinner />
            ) : survivalCurve ? (
              <div>
                {survivalCurve.median_survival_days && (
                  <p className="text-sm text-foreground mb-2">
                    Median risk persistence: <strong>{survivalCurve.median_survival_days} days</strong>
                  </p>
                )}
                {survivalCurve.timeline_days && survivalCurve.timeline_days.length > 0 ? (
                  <div className="bg-muted rounded-lg p-3">
                    <p className="text-xs text-muted-foreground mb-2">Survival Curve (probability risk remains open over time)</p>
                    <div className="flex items-end gap-1 h-24">
                      {survivalCurve.timeline_days.slice(0, 20).map((day, i) => (
                        <div
                          key={i}
                          className="flex-1 bg-indigo-400 rounded-t"
                          style={{ height: `${(survivalCurve.survival_probability[i] || 0) * 100}%` }}
                          title={`Day ${day}: ${((survivalCurve.survival_probability[i] || 0) * 100).toFixed(0)}%`}
                        />
                      ))}
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>Day 0</span>
                      <span>Day {survivalCurve.timeline_days[survivalCurve.timeline_days.length - 1] || '?'}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No survival data available yet.</p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Unable to load survival data.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Inline score badge for threat cards
export function MLScoreBadge({ threatId }: { threatId: string }) {
  const [explanation, setExplanation] = useState<MLExplanation | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    apiClient.explainThreatScore(threatId).then(setExplanation).catch(() => {});
  }, [threatId]);

  if (!explanation || explanation.likelihood_score === undefined) return null;

  const score = explanation.likelihood_score;

  return (
    <div className="relative inline-flex">
      <button
        onClick={(e) => { e.stopPropagation(); setShowDetails(!showDetails); }}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border cursor-pointer ${
          score >= 80 ? 'bg-red-100 text-red-700 border-red-200'
          : score >= 60 ? 'bg-amber-100 text-amber-700 border-amber-200'
          : score >= 40 ? 'bg-yellow-100 text-yellow-700 border-yellow-200'
          : 'bg-green-100 text-green-700 border-green-200'
        }`}
      >
        <TrendingUp className="w-3 h-3" />
        ML: {score.toFixed(0)}
      </button>
      {showDetails && explanation.components && explanation.components.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-card border border-border rounded-lg shadow-lg p-3 z-50" onClick={(e) => e.stopPropagation()}>
          <p className="text-xs font-semibold text-foreground mb-2">Score Breakdown ({explanation.total_points.toFixed(1)}/{explanation.max_possible})</p>
          {explanation.components.slice(0, 5).map((c, i) => (
            <div key={i} className="flex items-center justify-between text-xs py-0.5">
              <span className="text-muted-foreground">{c.feature}</span>
              <span className={c.points > 0 ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}>
                +{c.points.toFixed(1)}/{c.max}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
