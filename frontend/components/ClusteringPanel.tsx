'use client';

import { useState, useCallback, useEffect } from 'react';
import { Boxes, RefreshCw, Search, ChevronDown, ChevronRight, Layers, Crosshair } from 'lucide-react';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';
import apiClient from '../lib/api-client';
import type { ClusteringResponse, ClusterThreat, SimilarThreatsResponse } from '../lib/types';

interface ClusteringPanelProps {
  assessmentId: string;
}

const CLUSTER_COLORS = [
  'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300',
  'bg-purple-100 dark:bg-purple-900/30 border-purple-300 dark:border-purple-700 text-purple-800 dark:text-purple-300',
  'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-300',
  'bg-amber-100 dark:bg-amber-900/30 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300',
  'bg-rose-100 dark:bg-rose-900/30 border-rose-300 dark:border-rose-700 text-rose-800 dark:text-rose-300',
  'bg-cyan-100 dark:bg-cyan-900/30 border-cyan-300 dark:border-cyan-700 text-cyan-800 dark:text-cyan-300',
  'bg-indigo-100 dark:bg-indigo-900/30 border-indigo-300 dark:border-indigo-700 text-indigo-800 dark:text-indigo-300',
  'bg-lime-100 dark:bg-lime-900/30 border-lime-300 dark:border-lime-700 text-lime-800 dark:text-lime-300',
];

export function ClusteringPanel({ assessmentId }: ClusteringPanelProps) {
  const [clusters, setClusters] = useState<ClusteringResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCluster, setExpandedCluster] = useState<number | null>(null);
  const [similarSearch, setSimilarSearch] = useState<string>('');
  const [similarResults, setSimilarResults] = useState<SimilarThreatsResponse | null>(null);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  const loadClusters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.clusterAssessment(assessmentId);
      setClusters(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Clustering failed');
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadClusters();
  }, [loadClusters]);

  const handleFindSimilar = async (threatId: string) => {
    try {
      setLoadingSimilar(true);
      const data = await apiClient.findSimilarThreats(threatId, 5);
      setSimilarResults(data);
    } catch {
      setSimilarResults(null);
    } finally {
      setLoadingSimilar(false);
    }
  };

  return (
    <div className="bg-card rounded-lg border border-border p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
            <Boxes className="w-5 h-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Threat Clusters</h3>
            <p className="text-sm text-muted-foreground">DBSCAN density-based clustering of similar threats</p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={loadClusters} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Re-cluster
        </Button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 rounded-lg text-sm text-red-700 dark:text-red-400 mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : clusters ? (
        <div>
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="p-3 bg-muted rounded-lg text-center">
              <p className="text-xs text-muted-foreground mb-1">Clusters</p>
              <p className="text-lg font-bold text-foreground">{clusters.clusters_found}</p>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <p className="text-xs text-muted-foreground mb-1">Total Threats</p>
              <p className="text-lg font-bold text-foreground">{clusters.quality?.n_threats || 0}</p>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <p className="text-xs text-muted-foreground mb-1">Outliers</p>
              <p className="text-lg font-bold text-amber-600 dark:text-amber-400">{clusters.quality?.n_outliers || 0}</p>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <p className="text-xs text-muted-foreground mb-1">Scope</p>
              <p className="text-lg font-bold text-green-600 dark:text-green-400 capitalize">
                {clusters.scope || 'N/A'}
              </p>
            </div>
          </div>

          {/* Cluster list — group threats by cluster_id */}
          {(() => {
            const grouped = new Map<number, ClusterThreat[]>();
            const outliers: ClusterThreat[] = [];
            (clusters.threats || []).forEach((t) => {
              if (t.is_outlier) {
                outliers.push(t);
              } else {
                const existing = grouped.get(t.cluster_id) || [];
                existing.push(t);
                grouped.set(t.cluster_id, existing);
              }
            });
            const clusterEntries = Array.from(grouped.entries()).sort(([a], [b]) => a - b);

            return clusterEntries.length > 0 ? (
              <div className="space-y-3">
                {clusterEntries.map(([clusterId, threats], idx) => (
                  <div
                    key={clusterId}
                    className={`rounded-lg border p-4 ${CLUSTER_COLORS[idx % CLUSTER_COLORS.length]}`}
                  >
                    <button
                      onClick={() => setExpandedCluster(expandedCluster === clusterId ? null : clusterId)}
                      className="w-full flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <Layers className="w-4 h-4" />
                        <span className="text-sm font-semibold">
                          Cluster {clusterId + 1}
                        </span>
                        <span className="text-xs opacity-70">
                          ({threats.length} threat{threats.length !== 1 ? 's' : ''})
                        </span>
                      </div>
                      {expandedCluster === clusterId ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </button>
                    {expandedCluster === clusterId && (
                      <div className="mt-3 space-y-1.5">
                        {threats.map((t) => (
                          <div
                            key={t.threat_id}
                            className="flex items-center justify-between p-2 bg-card/60 rounded border border-card/80"
                          >
                            <span className="text-sm text-foreground truncate flex-1">
                              {t.title || t.threat_id.slice(0, 12)}
                            </span>
                            <div className="flex items-center gap-2 shrink-0">
                              {t.likelihood_score !== undefined && (
                                <span className="text-xs text-muted-foreground">Score: {t.likelihood_score}</span>
                              )}
                              <button
                                onClick={(e) => { e.stopPropagation(); handleFindSimilar(t.threat_id); }}
                                className="p-1 hover:bg-card rounded text-muted-foreground hover:text-blue-600 dark:hover:text-blue-400 transition"
                                title="Find similar threats"
                              >
                                <Crosshair className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                {outliers.length > 0 && (
                  <div className="rounded-lg border p-4 bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-300">
                    <div className="flex items-center gap-2 mb-2">
                      <Layers className="w-4 h-4" />
                      <span className="text-sm font-semibold">Outliers</span>
                      <span className="text-xs opacity-70">({outliers.length} threat{outliers.length !== 1 ? 's' : ''})</span>
                    </div>
                    <div className="space-y-1.5">
                      {outliers.map((t) => (
                        <div key={t.threat_id} className="flex items-center justify-between p-2 bg-card/60 rounded border border-card/80">
                          <span className="text-sm text-foreground truncate flex-1">{t.title || t.threat_id.slice(0, 12)}</span>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleFindSimilar(t.threat_id); }}
                            className="p-1 hover:bg-card rounded text-muted-foreground hover:text-blue-600 dark:hover:text-blue-400 transition"
                            title="Find similar threats"
                          >
                            <Crosshair className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No clusters formed. Try enriching more threats or adjusting parameters.
              </p>
            );
          })()}

          {/* Similar threats result */}
          {similarResults && (
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/40 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Crosshair className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-semibold text-blue-800 dark:text-blue-300">Similar Threats</span>
              </div>
              {similarResults.similar_threats.length === 0 ? (
                <p className="text-sm text-blue-600 dark:text-blue-400">No similar threats found.</p>
              ) : (
                <div className="space-y-1.5">
                  {similarResults.similar_threats.map((s) => (
                    <div key={s.threat_id} className="flex items-center justify-between p-2 bg-card rounded border border-blue-100 dark:border-blue-800/30">
                      <span className="text-sm text-foreground truncate flex-1">{s.title || s.threat_id.slice(0, 12)}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-blue-500"
                            style={{ width: `${s.similarity * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-blue-700 dark:text-blue-400">{(s.similarity * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
