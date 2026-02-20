'use client';

/**
 * KillChainFlow – interactive React Flow canvas for ATT&CK kill chain stages.
 *
 * Architecture:
 *   - Each stage is a custom node (StageNode) showing tactic + technique + MITRE ID
 *   - Nodes are laid out left-to-right (linear kill chain progression)
 *   - Edge connects each consecutive stage
 *   - Clicking a node opens a detail drawer (description, adversary behavior, detection)
 *   - Built-in zoom/pan via React Flow Controls
 */

import { useState, useMemo, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react';
import {
  ExternalLink,
  Zap,
  Eye,
  Target,
  Trash2,
  Loader2,
  X,
  FileText,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import type { KillChain, KillChainStage } from '../lib/types';

// ── Tactic colour palette (ATT&CK standard, dark theme) ────────────────────

interface TacticColors {
  bg: string;
  border: string;
  text: string;
  headerBg: string;
  borderHex: string;
}

const TACTIC_COLORS: Record<string, TacticColors> = {
  'reconnaissance':       { bg: '#0f172a', border: '#475569', text: '#cbd5e1', headerBg: '#1e293b', borderHex: '#475569' },
  'resource-development': { bg: '#111827', border: '#52525b', text: '#d4d4d8', headerBg: '#27272a', borderHex: '#52525b' },
  'initial-access':       { bg: '#1c0a0a', border: '#dc2626', text: '#fca5a5', headerBg: '#450a0a', borderHex: '#dc2626' },
  'execution':            { bg: '#1a0d05', border: '#ea580c', text: '#fdba74', headerBg: '#431407', borderHex: '#ea580c' },
  'persistence':          { bg: '#1a0f00', border: '#d97706', text: '#fcd34d', headerBg: '#451a03', borderHex: '#d97706' },
  'privilege-escalation': { bg: '#1a1100', border: '#ca8a04', text: '#fde047', headerBg: '#422006', borderHex: '#ca8a04' },
  'defense-evasion':      { bg: '#0d1a00', border: '#65a30d', text: '#bef264', headerBg: '#1a2e05', borderHex: '#65a30d' },
  'credential-access':    { bg: '#001a0d', border: '#16a34a', text: '#86efac', headerBg: '#052e16', borderHex: '#16a34a' },
  'discovery':            { bg: '#00191a', border: '#0d9488', text: '#5eead4', headerBg: '#042f2e', borderHex: '#0d9488' },
  'lateral-movement':     { bg: '#001a22', border: '#0891b2', text: '#67e8f9', headerBg: '#083344', borderHex: '#0891b2' },
  'collection':           { bg: '#001828', border: '#0284c7', text: '#7dd3fc', headerBg: '#082f49', borderHex: '#0284c7' },
  'command-and-control':  { bg: '#000d2b', border: '#2563eb', text: '#93c5fd', headerBg: '#172554', borderHex: '#2563eb' },
  'exfiltration':         { bg: '#0e0026', border: '#7c3aed', text: '#c4b5fd', headerBg: '#2e1065', borderHex: '#7c3aed' },
  'impact':               { bg: '#15002e', border: '#9333ea', text: '#d8b4fe', headerBg: '#3b0764', borderHex: '#9333ea' },
};

function getTacticColors(tacticName: string): TacticColors {
  const key = tacticName.toLowerCase().replace(/\s+/g, '-');
  return TACTIC_COLORS[key] ?? {
    bg: '#111827', border: '#4b5563', text: '#d1d5db', headerBg: '#1f2937', borderHex: '#4b5563',
  };
}

// ── Custom React Flow node ──────────────────────────────────────────────────

type StageNodeData = Node<{ stage: KillChainStage }, 'stageNode'>;

const NODE_W = 190;
const NODE_H = 115;

function StageNode({ data, selected }: NodeProps<StageNodeData>) {
  const { stage } = data;
  const c = getTacticColors(stage.tactic_name);
  return (
    <div
      style={{
        width: NODE_W,
        height: NODE_H,
        background: c.bg,
        border: `2px solid ${selected ? '#ffffff' : c.borderHex}`,
        borderRadius: 10,
        overflow: 'hidden',
        boxShadow: selected
          ? `0 0 0 3px ${c.borderHex}, 0 8px 24px rgba(0,0,0,0.6)`
          : '0 4px 14px rgba(0,0,0,0.5)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Tactic header band */}
      <div style={{
        background: c.headerBg,
        borderBottom: `1px solid ${c.borderHex}`,
        padding: '5px 10px',
        flexShrink: 0,
      }}>
        <p style={{ color: c.text, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {stage.tactic_name}
        </p>
      </div>

      {/* Technique name */}
      <div style={{ padding: '8px 10px 4px', flex: 1 }}>
        <p style={{ color: '#f3f4f6', fontSize: 11, fontWeight: 600, margin: 0, lineHeight: 1.35, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {stage.technique_name || '—'}
        </p>
      </div>

      {/* MITRE ID chip */}
      <div style={{ padding: '0 10px 6px', flexShrink: 0 }}>
        {stage.mitre_id ? (
          <span style={{ color: c.text, background: `${c.borderHex}33`, border: `1px solid ${c.borderHex}`, borderRadius: 4, fontSize: 9, fontFamily: 'monospace', fontWeight: 700, padding: '2px 6px' }}>
            {stage.mitre_id}
          </span>
        ) : (
          <span style={{ color: '#6b7280', fontSize: 9 }}>—</span>
        )}
      </div>

      {/* Hint bar */}
      <div style={{ borderTop: '1px solid #374151', padding: '3px 10px', flexShrink: 0 }}>
        <p style={{ color: '#6b7280', fontSize: 9, margin: 0 }}>Click to expand</p>
      </div>

      <Handle type="target" position={Position.Left} style={{ background: '#6b7280', width: 8, height: 8, border: 'none' }} />
      <Handle type="source" position={Position.Right} style={{ background: '#6b7280', width: 8, height: 8, border: 'none' }} />
    </div>
  );
}

const nodeTypes = { stageNode: StageNode };

// ── Detail drawer component ─────────────────────────────────────────────────

function StageDrawer({ stage, onClose }: { stage: KillChainStage; onClose: () => void }) {
  const c = getTacticColors(stage.tactic_name);
  const mitreUrl = stage.mitre_id
    ? `https://attack.mitre.org/techniques/${stage.mitre_id.replace('.', '/')}/`
    : null;

  return (
    <div className="absolute right-0 top-0 h-full w-72 bg-gray-900 border-l border-gray-700 shadow-2xl z-20 flex flex-col">
      {/* Header */}
      <div
        className="px-4 py-3 border-b flex items-start justify-between gap-2 flex-shrink-0"
        style={{ background: c.headerBg, borderColor: c.borderHex }}
      >
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest truncate" style={{ color: c.text }}>
            Stage {stage.stage_number} · {stage.tactic_name}
          </p>
          <p className="text-sm font-bold text-white mt-0.5 leading-snug">
            {stage.technique_name || '—'}
          </p>
          {stage.mitre_id && mitreUrl && (
            <a
              href={mitreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-mono mt-1 hover:underline"
              style={{ color: c.text }}
            >
              {stage.mitre_id} <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white flex-shrink-0 mt-0.5">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {stage.description && (
          <section>
            <h5 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-1 mb-1.5">
              <FileText className="w-3 h-3" /> Technique Description
            </h5>
            <p className="text-xs text-gray-300 leading-relaxed">{stage.description}</p>
          </section>
        )}
        {stage.actor_behavior && (
          <section>
            <h5 className="text-[11px] font-semibold text-orange-400 uppercase tracking-wide flex items-center gap-1 mb-1.5">
              <Zap className="w-3 h-3" /> Adversary Behaviour
            </h5>
            <p className="text-xs text-gray-300 leading-relaxed">{stage.actor_behavior}</p>
          </section>
        )}
        {stage.detection_hint && (
          <section>
            <h5 className="text-[11px] font-semibold text-green-400 uppercase tracking-wide flex items-center gap-1 mb-1.5">
              <Eye className="w-3 h-3" /> Detection Guidance
            </h5>
            <p className="text-xs text-gray-300 leading-relaxed">{stage.detection_hint}</p>
          </section>
        )}
        {!stage.description && !stage.actor_behavior && !stage.detection_hint && (
          <p className="text-xs text-gray-500 italic">No additional detail available for this stage.</p>
        )}
      </div>
    </div>
  );
}

// ── Fullscreen overlay ──────────────────────────────────────────────────────

interface FullscreenFlowProps {
  killChain: KillChain;
  onClose: () => void;
}

function FullscreenFlow({ killChain, onClose }: FullscreenFlowProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedStage = selectedId
    ? killChain.stages.find((s) => s.id === selectedId) ?? null
    : null;

  const nodes: Node[] = useMemo(
    () =>
      killChain.stages.map((stage, idx) => ({
        id: stage.id,
        type: 'stageNode',
        position: { x: idx * (NODE_W + H_GAP), y: 60 },
        selectable: true,
        selected: stage.id === selectedId,
        data: { stage } as unknown as Record<string, unknown>,
      })),
    [killChain.stages, selectedId],
  );

  const edges: Edge[] = useMemo(
    () =>
      killChain.stages.slice(0, -1).map((stage, idx) => ({
        id: `e-fs-${idx}`,
        source: stage.id,
        target: killChain.stages[idx + 1].id,
        type: 'smoothstep',
        style: { stroke: '#4b5563', strokeWidth: 2 },
      })),
    [killChain.stages],
  );

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  // Prevent body scroll while fullscreen is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  if (typeof window === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex flex-col bg-gray-950"
      style={{ fontFamily: 'inherit' }}
    >
      {/* Fullscreen header */}
      <div className="flex items-start justify-between px-5 py-3 border-b border-gray-800 flex-shrink-0 bg-gray-900">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Target className="w-4 h-4 text-red-400 flex-shrink-0" />
            <h3 className="text-sm font-bold text-white">{killChain.scenario_name}</h3>
            {killChain.threat_actor && (
              <span className="text-xs bg-red-900/40 border border-red-800 text-red-300 px-2 py-0.5 rounded-full">
                {killChain.threat_actor}
              </span>
            )}
            <span className="text-xs bg-gray-800 border border-gray-600 text-gray-400 px-2 py-0.5 rounded-full">
              {killChain.stages.length} stage{killChain.stages.length !== 1 ? 's' : ''} · ATT&amp;CK validated
            </span>
          </div>
          {killChain.description && (
            <p className="text-xs text-gray-400 mt-1 leading-snug">{killChain.description}</p>
          )}
          <p className="text-[11px] text-gray-600 mt-0.5">
            {selectedStage ? 'Click another stage or click selected to close' : 'Click a stage to inspect · Press Esc to close fullscreen'}
          </p>
        </div>
        <button
          onClick={onClose}
          className="ml-4 flex-shrink-0 inline-flex items-center gap-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 px-3 py-1.5 rounded-lg transition-colors"
          title="Exit fullscreen (Esc)"
        >
          <Minimize2 className="w-3.5 h-3.5" />
          Exit Fullscreen
        </button>
      </div>

      {/* Full canvas */}
      <div className="relative flex-1 min-h-0">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          onNodeClick={(_evt, node) =>
            setSelectedId((prev) => (prev === node.id ? null : node.id))
          }
          onPaneClick={() => setSelectedId(null)}
        >
          <Background color="#374151" gap={24} size={1} />
          <Controls showInteractive={false} style={{ bottom: 16, left: 16 }} />
        </ReactFlow>

        {selectedStage && (
          <StageDrawer stage={selectedStage} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>,
    document.body,
  );
}

// ── Main component ──────────────────────────────────────────────────────────

interface KillChainFlowProps {
  killChain: KillChain;
  onDelete?: (id: string) => Promise<void>;
}

const H_GAP = 60;
const CANVAS_H = 220;

export function KillChainFlow({ killChain, onDelete }: KillChainFlowProps) {
  const [deleting, setDeleting] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const openFullscreen = useCallback(() => setFullscreen(true), []);
  const closeFullscreen = useCallback(() => setFullscreen(false), []);

  const selectedStage = selectedId
    ? killChain.stages.find((s) => s.id === selectedId) ?? null
    : null;

  const nodes: Node[] = useMemo(
    () =>
      killChain.stages.map((stage, idx) => ({
        id: stage.id,
        type: 'stageNode',
        position: { x: idx * (NODE_W + H_GAP), y: (CANVAS_H - NODE_H) / 2 - 20 },
        selectable: true,
        selected: stage.id === selectedId,
        data: { stage } as unknown as Record<string, unknown>,
      })),
    [killChain.stages, selectedId],
  );

  const edges: Edge[] = useMemo(
    () =>
      killChain.stages.slice(0, -1).map((stage, idx) => ({
        id: `e-${idx}`,
        source: stage.id,
        target: killChain.stages[idx + 1].id,
        type: 'smoothstep',
        style: { stroke: '#4b5563', strokeWidth: 2 },
      })),
    [killChain.stages],
  );

  async function handleDelete() {
    if (!onDelete) return;
    if (!confirm('Delete this scenario?')) return;
    setDeleting(true);
    try {
      await onDelete(killChain.id);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden">
      {/* Scenario header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-gray-800">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Target className="w-4 h-4 text-red-400 flex-shrink-0" />
            <h4 className="text-sm font-bold text-white">{killChain.scenario_name}</h4>
            {killChain.threat_actor && (
              <span className="text-xs bg-red-900/40 border border-red-800 text-red-300 px-2 py-0.5 rounded-full">
                {killChain.threat_actor}
              </span>
            )}
            <span className="text-xs bg-gray-800 border border-gray-600 text-gray-400 px-2 py-0.5 rounded-full">
              {killChain.stages.length} stage{killChain.stages.length !== 1 ? 's' : ''} · ATT&amp;CK validated
            </span>
          </div>
          {killChain.description && (
            <p className="text-xs text-gray-400 mt-1 leading-snug">{killChain.description}</p>
          )}
          <p className="text-[11px] text-gray-600 mt-0.5">
            {new Date(killChain.created_at).toLocaleDateString()} ·{' '}
            {selectedStage ? 'Click another stage or click selected to close' : 'Click a stage to inspect'}
          </p>
        </div>
        <div className="flex items-center gap-2 ml-3 flex-shrink-0">
          <button
            onClick={openFullscreen}
            className="text-gray-500 hover:text-white transition-colors"
            title="Expand to full screen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          {onDelete && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-gray-600 hover:text-red-400 disabled:opacity-40 transition-colors"
              title="Delete scenario"
            >
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Fullscreen overlay (portal) */}
      {fullscreen && (
        <FullscreenFlow killChain={killChain} onClose={closeFullscreen} />
      )}

      {/* React Flow canvas with detail drawer overlay */}
      <div className="relative" style={{ height: CANVAS_H }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.8}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          onNodeClick={(_evt, node) =>
            setSelectedId((prev) => (prev === node.id ? null : node.id))
          }
          onPaneClick={() => setSelectedId(null)}
        >
          <Background color="#374151" gap={20} size={1} />
          <Controls
            showInteractive={false}
            style={{ bottom: 10, left: 10 }}
          />
        </ReactFlow>

        {/* Slide-in detail drawer */}
        {selectedStage && (
          <StageDrawer stage={selectedStage} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>
  );
}
