'use client';

import { useState, useCallback, useEffect } from 'react';
import { Network, RefreshCw, Star, Route, ZoomIn, ZoomOut, Maximize2, AlertTriangle } from 'lucide-react';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';
import apiClient from '../lib/api-client';
import type { AssessmentGraph, GraphNode, GraphEdge, CriticalNode } from '../lib/types';

interface ThreatGraphPanelProps {
  assessmentId: string;
}

const NODE_COLORS: Record<string, string> = {
  threat: '#ef4444',
  technique: '#8b5cf6',
  tactic: '#3b82f6',
  cve: '#f59e0b',
  assessment: '#10b981',
  default: '#6b7280',
};

const NODE_BG: Record<string, string> = {
  threat: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-800 dark:text-red-300',
  technique: 'bg-purple-100 dark:bg-purple-900/30 border-purple-300 dark:border-purple-700 text-purple-800 dark:text-purple-300',
  tactic: 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300',
  cve: 'bg-amber-100 dark:bg-amber-900/30 border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300',
  assessment: 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700 text-green-800 dark:text-green-300',
  default: 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-300',
};

export function ThreatGraphPanel({ assessmentId }: ThreatGraphPanelProps) {
  const [graph, setGraph] = useState<AssessmentGraph | null>(null);
  const [criticalNodes, setCriticalNodes] = useState<CriticalNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [view, setView] = useState<'graph' | 'critical'>('graph');

  const loadGraph = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [graphData, criticalData] = await Promise.all([
        apiClient.getAssessmentGraph(assessmentId),
        apiClient.getCriticalNodes(assessmentId, 10),
      ]);
      setGraph(graphData);
      setCriticalNodes(criticalData.critical_nodes || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load graph');
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const getNodeStyle = (type: string) => NODE_BG[type] || NODE_BG.default;

  return (
    <div className="bg-card rounded-lg border border-border p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
            <Network className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Threat Knowledge Graph</h3>
            <p className="text-sm text-muted-foreground">Relationship mapping with PageRank analysis</p>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-muted rounded-lg p-0.5">
            <button
              onClick={() => setView('graph')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                view === 'graph' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
              }`}
            >
              Graph
            </button>
            <button
              onClick={() => setView('critical')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                view === 'critical' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
              }`}
            >
              Critical Nodes
            </button>
          </div>
          <Button variant="ghost" size="sm" onClick={loadGraph} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
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
      ) : view === 'graph' && graph ? (
        <div>
          {/* Stats bar */}
          <div className="flex gap-4 mb-4 text-sm">
            <span className="text-muted-foreground">
              <strong className="text-foreground">{graph.stats.node_count}</strong> nodes
            </span>
            <span className="text-muted-foreground">
              <strong className="text-foreground">{graph.stats.edge_count}</strong> edges
            </span>
          </div>

          {/* Legend */}
          <div className="flex gap-3 mb-4 flex-wrap">
            {Object.entries(NODE_COLORS).filter(([k]) => k !== 'default').map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="capitalize text-muted-foreground">{type}</span>
              </div>
            ))}
          </div>

          {/* Visual graph layout */}
          <div className="relative bg-muted rounded-lg border border-border p-4 min-h-[320px] overflow-auto">
            {graph.nodes.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-muted-foreground">
                <div className="text-center">
                  <Network className="w-12 h-12 mx-auto mb-2 text-muted-foreground/50" />
                  <p>No graph data available. Enrich threats first.</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Group by type */}
                {['threat', 'technique', 'tactic', 'cve'].map((type) => {
                  const nodesOfType = graph.nodes.filter((n) => n.type === type);
                  if (nodesOfType.length === 0) return null;
                  return (
                    <div key={type}>
                      <p className="text-xs font-semibold text-muted-foreground uppercase mb-1.5">{type}s ({nodesOfType.length})</p>
                      <div className="flex flex-wrap gap-2">
                        {nodesOfType.map((node) => (
                          <button
                            key={node.id}
                            onClick={() => setSelectedNode(selectedNode?.id === node.id ? null : node)}
                            className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${getNodeStyle(node.type)} ${
                              selectedNode?.id === node.id ? 'ring-2 ring-offset-1 ring-blue-400 scale-105' : 'hover:scale-105'
                            }`}
                          >
                            {node.label}
                            {node.pagerank && node.pagerank > 0.05 && (
                              <Star className="w-3 h-3 inline ml-1 text-amber-500" />
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}

                {/* Show edges for selected node */}
                {selectedNode && (
                  <div className="mt-4 p-3 bg-card rounded-lg border border-blue-200 dark:border-blue-800/40">
                    <p className="text-sm font-semibold text-foreground mb-2">
                      Connections for: <span className="text-blue-600 dark:text-blue-400">{selectedNode.label}</span>
                    </p>
                    <div className="space-y-1">
                      {graph.edges
                        .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                        .map((edge, i) => {
                          const otherNodeId = edge.source === selectedNode.id ? edge.target : edge.source;
                          const otherNode = graph.nodes.find((n) => n.id === otherNodeId);
                          return (
                            <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
                              <Route className="w-3 h-3 text-muted-foreground/60" />
                              <span className="text-muted-foreground/60">{edge.relationship}</span>
                              <span className={`px-1.5 py-0.5 rounded ${getNodeStyle(otherNode?.type || 'default')}`}>
                                {otherNode?.label || otherNodeId}
                              </span>
                            </div>
                          );
                        })}
                      {graph.edges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id).length === 0 && (
                        <p className="text-xs text-muted-foreground">No connections found</p>
                      )}
                    </div>
                    {selectedNode.pagerank !== undefined && (
                      <div className="flex gap-4 mt-2 text-xs text-muted-foreground border-t border-border pt-2">
                        <span>PageRank: <strong>{selectedNode.pagerank.toFixed(4)}</strong></span>
                        {selectedNode.betweenness !== undefined && (
                          <span>Betweenness: <strong>{selectedNode.betweenness.toFixed(4)}</strong></span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : view === 'critical' ? (
        <div>
          <p className="text-sm text-muted-foreground mb-4">
            Nodes ranked by combined PageRank + betweenness centrality. These represent the most influential
            and structurally important elements in your threat landscape.
          </p>
          {criticalNodes.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No critical nodes found. Build the graph first.</p>
          ) : (
            <div className="space-y-2">
              {criticalNodes.map((node, index) => (
                <div
                  key={node.id}
                  className="flex items-center gap-4 p-3 bg-muted rounded-lg border border-border hover:bg-muted/80 transition"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    index === 0 ? 'bg-red-500 text-white' :
                    index === 1 ? 'bg-amber-500 text-white' :
                    index === 2 ? 'bg-yellow-400 text-gray-900' :
                    'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">{node.label}</p>
                    <p className="text-xs text-muted-foreground capitalize">{node.type}</p>
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground shrink-0">
                    <div className="text-center">
                      <p className="font-bold text-foreground">{node.pagerank.toFixed(4)}</p>
                      <p>PageRank</p>
                    </div>
                    <div className="text-center">
                      <p className="font-bold text-foreground">{node.betweenness.toFixed(4)}</p>
                      <p>Betweenness</p>
                    </div>
                    <div className="text-center">
                      <p className="font-bold text-indigo-700 dark:text-indigo-400">{node.composite_score.toFixed(4)}</p>
                      <p>Combined</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
