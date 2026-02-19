'use client';

/**
 * KillChainFlow – renders a MITRE ATT&CK kill chain as a visual horizontal flow.
 *
 * Each stage card shows: tactic, technique, MITRE ID, actor behaviour,
 * detection hint and a brief description.  Stages are connected with arrows.
 */

import { useState } from 'react';
import {
  ChevronRight,
  Eye,
  Zap,
  Target,
  AlertTriangle,
  Shield,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Trash2,
  Loader2,
} from 'lucide-react';
import type { KillChain, KillChainStage } from '../lib/types';

// Tactic colour mapping (ATT&CK standard palette adapted for dark theme)
const TACTIC_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  'reconnaissance':       { bg: 'bg-slate-800',   border: 'border-slate-600',  text: 'text-slate-200' },
  'resource-development': { bg: 'bg-zinc-800',    border: 'border-zinc-600',   text: 'text-zinc-200' },
  'initial-access':       { bg: 'bg-red-900/50',  border: 'border-red-700',    text: 'text-red-200' },
  'execution':            { bg: 'bg-orange-900/50', border: 'border-orange-700', text: 'text-orange-200' },
  'persistence':          { bg: 'bg-amber-900/50', border: 'border-amber-700', text: 'text-amber-200' },
  'privilege-escalation': { bg: 'bg-yellow-900/50', border: 'border-yellow-700', text: 'text-yellow-200' },
  'defense-evasion':      { bg: 'bg-lime-900/50', border: 'border-lime-700',   text: 'text-lime-200' },
  'credential-access':    { bg: 'bg-green-900/50', border: 'border-green-700', text: 'text-green-200' },
  'discovery':            { bg: 'bg-teal-900/50', border: 'border-teal-700',   text: 'text-teal-200' },
  'lateral-movement':     { bg: 'bg-cyan-900/50', border: 'border-cyan-700',   text: 'text-cyan-200' },
  'collection':           { bg: 'bg-sky-900/50',  border: 'border-sky-700',    text: 'text-sky-200' },
  'command-and-control':  { bg: 'bg-blue-900/50', border: 'border-blue-700',   text: 'text-blue-200' },
  'exfiltration':         { bg: 'bg-violet-900/50', border: 'border-violet-700', text: 'text-violet-200' },
  'impact':               { bg: 'bg-purple-900/50', border: 'border-purple-700', text: 'text-purple-200' },
};

function getTacticColor(tacticName: string) {
  const key = tacticName.toLowerCase().replace(/\s+/g, '-');
  return TACTIC_COLORS[key] ?? { bg: 'bg-gray-800', border: 'border-gray-600', text: 'text-gray-200' };
}

interface StageCardProps {
  stage: KillChainStage;
  isLast: boolean;
}

function StageCard({ stage, isLast }: StageCardProps) {
  const [expanded, setExpanded] = useState(false);
  const colors = getTacticColor(stage.tactic_name);

  return (
    <div className="flex items-stretch gap-0">
      {/* Stage card */}
      <div
        className={`flex-1 rounded-lg border ${colors.bg} ${colors.border} overflow-hidden min-w-[160px] max-w-[220px]`}
      >
        {/* Tactic header */}
        <div className={`px-3 py-1.5 border-b ${colors.border}`}>
          <p className={`text-xs font-bold uppercase tracking-wide ${colors.text}`}>
            {stage.tactic_name}
          </p>
        </div>

        {/* Technique name + MITRE ID */}
        <div className="px-3 pt-2 pb-1">
          <p className="text-sm font-semibold text-white leading-snug">
            {stage.technique_name || '—'}
          </p>
          {stage.mitre_id && (
            <a
              href={`https://attack.mitre.org/techniques/${stage.mitre_id.replace('.', '/')}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-xs text-blue-400 hover:text-blue-300 mt-0.5"
            >
              {stage.mitre_id}
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>

        {/* Short description */}
        {stage.description && (
          <p className="px-3 pb-2 text-xs text-gray-400 leading-snug">{stage.description}</p>
        )}

        {/* Expand/collapse for detail */}
        {(stage.actor_behavior || stage.detection_hint) && (
          <>
            <button
              onClick={() => setExpanded((e) => !e)}
              className="w-full flex items-center justify-between px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300 border-t border-gray-700 transition-colors"
            >
              <span>Details</span>
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {expanded && (
              <div className="px-3 pb-3 space-y-2 border-t border-gray-800">
                {stage.actor_behavior && (
                  <div>
                    <p className="text-xs font-semibold text-orange-400 flex items-center gap-1 mt-2">
                      <Zap className="w-3 h-3" /> Actor behaviour
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5 leading-snug">
                      {stage.actor_behavior}
                    </p>
                  </div>
                )}
                {stage.detection_hint && (
                  <div>
                    <p className="text-xs font-semibold text-green-400 flex items-center gap-1">
                      <Eye className="w-3 h-3" /> Detection hint
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5 leading-snug">
                      {stage.detection_hint}
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Arrow connector */}
      {!isLast && (
        <div className="flex items-center px-1 flex-shrink-0">
          <ChevronRight className="w-5 h-5 text-gray-600" />
        </div>
      )}
    </div>
  );
}

interface KillChainFlowProps {
  killChain: KillChain;
  onDelete?: (id: string) => Promise<void>;
}

export function KillChainFlow({ killChain, onDelete }: KillChainFlowProps) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!onDelete) return;
    if (!confirm('Delete this kill chain scenario?')) return;
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
      <div className="flex items-start justify-between p-4 border-b border-gray-800">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Target className="w-4 h-4 text-red-400 flex-shrink-0" />
            <h4 className="text-sm font-bold text-white">{killChain.scenario_name}</h4>
            {killChain.threat_actor && (
              <span className="text-xs bg-red-900/40 border border-red-800 text-red-300 px-2 py-0.5 rounded-full">
                {killChain.threat_actor}
              </span>
            )}
            {killChain.generated_by_ai && (
              <span className="text-xs bg-purple-900/40 border border-purple-800 text-purple-300 px-2 py-0.5 rounded-full">
                AI generated
              </span>
            )}
          </div>
          {killChain.description && (
            <p className="text-xs text-gray-400 mt-1">{killChain.description}</p>
          )}
          <p className="text-xs text-gray-600 mt-1">
            {killChain.stages.length} stages · generated{' '}
            {new Date(killChain.created_at).toLocaleDateString()}
          </p>
        </div>

        {onDelete && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="ml-3 flex-shrink-0 text-gray-600 hover:text-red-400 disabled:opacity-40 transition-colors"
            title="Delete scenario"
          >
            {deleting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Kill chain stages – horizontal scrollable flow */}
      <div className="p-4 overflow-x-auto">
        <div className="flex items-stretch gap-0 pb-2" style={{ minWidth: 'max-content' }}>
          {killChain.stages.map((stage, idx) => (
            <StageCard
              key={stage.id}
              stage={stage}
              isLast={idx === killChain.stages.length - 1}
            />
          ))}
        </div>
      </div>

      {/* Stage count legend */}
      <div className="px-4 pb-3 flex items-center gap-2 text-xs text-gray-600">
        <Shield className="w-3 h-3" />
        <span>{killChain.stages.length} attack stages</span>
        {killChain.model_id && <span>· {killChain.model_id}</span>}
      </div>
    </div>
  );
}
