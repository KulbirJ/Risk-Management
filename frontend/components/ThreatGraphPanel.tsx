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
  threat: 'bg-red-100 border-red-300 text-red-800',
  technique: 'bg-purple-100 border-purple-300 text-purple-800',
  tactic: 'bg-blue-100 border-blue-300 text-blue-800',
  cve: 'bg-amber-100 border-amber-300 text-amber-800',
  assessment: 'bg-green-100 border-green-300 text-green-800',
  default: 'bg-gray-100 border-gray-300 text-gray-800',
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
      setCriticalNodes(criticalData.top_critical || []);
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
    <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-emerald-100 rounded-lg">
            <Network className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Threat Knowledge Graph</h3>
            <p className="text-sm text-gray-500">Relationship mapping with PageRank analysis</p>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setView('graph')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                view === 'graph' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
              }`}
            >
              Graph
            </button>
            <button
              onClick={() => setView('critical')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition ${
                view === 'critical' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
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
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 mb-4">
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
            <span className="text-gray-600">
              <strong className="text-gray-900">{graph.node_count}</strong> nodes
            </span>
            <span className="text-gray-600">
              <strong className="text-gray-900">{graph.edge_count}</strong> edges
            </span>
          </div>

          {/* Legend */}
          <div className="flex gap-3 mb-4 flex-wrap">
            {Object.entries(NODE_COLORS).filter(([k]) => k !== 'default').map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                <span className="capitalize text-gray-600">{type}</span>
              </div>
            ))}
          </div>

          {/* Visual graph layout */}
          <div className="relative bg-gray-50 rounded-lg border border-gray-200 p-4 min-h-[320px] overflow-auto">
            {graph.nodes.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-gray-500">
                <div className="text-center">
                  <Network className="w-12 h-12 mx-auto mb-2 text-gray-300" />
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
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-1.5">{type}s ({nodesOfType.length})</p>
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
                  <div className="mt-4 p-3 bg-white rounded-lg border border-blue-200">
                    <p className="text-sm font-semibold text-gray-800 mb-2">
                      Connections for: <span className="text-blue-600">{selectedNode.label}</span>
                    </p>
                    <div className="space-y-1">
                      {graph.edges
                        .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                        .map((edge, i) => {
                          const otherNodeId = edge.source === selectedNode.id ? edge.target : edge.source;
                          const otherNode = graph.nodes.find((n) => n.id === otherNodeId);
                          return (
                            <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                              <Route className="w-3 h-3 text-gray-400" />
                              <span className="text-gray-400">{edge.relationship}</span>
                              <span className={`px-1.5 py-0.5 rounded ${getNodeStyle(otherNode?.type || 'default')}`}>
                                {otherNode?.label || otherNodeId}
                              </span>
                            </div>
                          );
                        })}
                      {graph.edges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id).length === 0 && (
                        <p className="text-xs text-gray-400">No connections found</p>
                      )}
                    </div>
                    {selectedNode.pagerank !== undefined && (
                      <div className="flex gap-4 mt-2 text-xs text-gray-500 border-t border-gray-100 pt-2">
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
          <p className="text-sm text-gray-600 mb-4">
            Nodes ranked by combined PageRank + betweenness centrality. These represent the most influential
            and structurally important elements in your threat landscape.
          </p>
          {criticalNodes.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">No critical nodes found. Build the graph first.</p>
          ) : (
            <div className="space-y-2">
              {criticalNodes.map((node, index) => (
                <div
                  key={node.id}
                  className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg border border-gray-100 hover:bg-gray-100 transition"
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    index === 0 ? 'bg-red-500 text-white' :
                    index === 1 ? 'bg-amber-500 text-white' :
                    index === 2 ? 'bg-yellow-400 text-gray-900' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">{node.label}</p>
                    <p className="text-xs text-gray-500 capitalize">{node.type}</p>
                  </div>
                  <div className="flex gap-4 text-xs text-gray-500 shrink-0">
                    <div className="text-center">
                      <p className="font-bold text-gray-700">{node.pagerank.toFixed(4)}</p>
                      <p>PageRank</p>
                    </div>
                    <div className="text-center">
                      <p className="font-bold text-gray-700">{node.betweenness.toFixed(4)}</p>
                      <p>Betweenness</p>
                    </div>
                    <div className="text-center">
                      <p className="font-bold text-indigo-700">{node.combined_score.toFixed(4)}</p>
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
