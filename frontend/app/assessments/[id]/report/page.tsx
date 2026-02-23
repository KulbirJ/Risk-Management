'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Printer, Shield, AlertTriangle, CheckCircle, TrendingUp, Globe, Cpu, Users, Target, ChevronRight, Activity } from 'lucide-react';
import apiClient from '../../../../lib/api-client';
import type { AssessmentReport, ThreatReportItem } from '../../../../lib/types';

// ─── Severity helpers ───────────────────────────────────────────────────────

const SEV_COLOUR: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high:     'bg-orange-100 text-orange-800 border-orange-200',
  medium:   'bg-yellow-100 text-yellow-800 border-yellow-200',
  low:      'bg-green-100 text-green-800 border-green-200',
};

const SEV_BAR: Record<string, string> = {
  critical: 'bg-red-500',
  high:     'bg-orange-500',
  medium:   'bg-yellow-400',
  low:      'bg-green-500',
};

const SEV_BORDER: Record<string, string> = {
  critical: 'border-l-red-500',
  high:     'border-l-orange-500',
  medium:   'border-l-yellow-400',
  low:      'border-l-green-500',
};

function SeverityBadge({ sev }: { sev: string }) {
  const s = (sev || 'medium').toLowerCase();
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border uppercase tracking-wide ${SEV_COLOUR[s] ?? SEV_COLOUR.medium}`}>
      {s}
    </span>
  );
}

function ScoreBar({ score, label, color = 'bg-blue-500' }: { score: number; label?: string; color?: string }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      {label && <span className="text-xs text-gray-500 w-8 text-right">{label}</span>}
    </div>
  );
}

// Inline severity distribution bar (CISO overview)
function SeverityDistBar({ stats }: { stats: AssessmentReport['stats'] }) {
  const total = stats.total || 1;
  const bars = [
    { key: 'critical', label: 'Critical', count: stats.critical, color: 'bg-red-500' },
    { key: 'high',     label: 'High',     count: stats.high,     color: 'bg-orange-500' },
    { key: 'medium',   label: 'Medium',   count: stats.medium,   color: 'bg-yellow-400' },
    { key: 'low',      label: 'Low',      count: stats.low,      color: 'bg-green-500' },
  ];
  return (
    <div className="space-y-2">
      {bars.map(b => (
        <div key={b.key} className="flex items-center gap-3">
          <span className="w-16 text-sm text-gray-600">{b.label}</span>
          <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${b.color}`}
              style={{ width: `${(b.count / total) * 100}%` }}
            />
          </div>
          <span className="w-6 text-sm font-semibold text-gray-700 text-right">{b.count}</span>
        </div>
      ))}
    </div>
  );
}

// Auto-generated executive key-findings bullets
function KeyFindings({ report }: { report: AssessmentReport }) {
  const { stats, threats } = report;
  const findings: string[] = [];

  if (stats.critical > 0)
    findings.push(`${stats.critical} critical-severity threat${stats.critical > 1 ? 's' : ''} require immediate remediation.`);
  if (stats.at_risk > 0)
    findings.push(`${stats.at_risk} threat${stats.at_risk > 1 ? 's are' : ' is'} actively tracked in the risk register.`);
  if (stats.with_exploits > 0)
    findings.push(`${stats.with_exploits} threat${stats.with_exploits > 1 ? 's have' : ' has'} confirmed public exploit code (GitHub PoC).`);
  if (stats.with_kill_chains > 0)
    findings.push(`AI-generated kill-chain scenarios available for ${stats.with_kill_chains} threat${stats.with_kill_chains > 1 ? 's' : ''}, enabling targeted tabletop exercises.`);
  if (stats.mitigated > 0)
    findings.push(`${stats.mitigated} threat${stats.mitigated > 1 ? 's have' : ' has'} been mitigated. Continue monitoring for regression.`);

  // Sector frequency finding
  const withSectorFreq = threats.filter(t => t.sector_frequency && Object.keys(t.sector_frequency).length > 0);
  if (withSectorFreq.length > 0 && report.industry_sector) {
    const topFreq = withSectorFreq.sort((a, b) => (b.sector_frequency.annual_frequency_per_1k ?? 0) - (a.sector_frequency.annual_frequency_per_1k ?? 0))[0];
    if (topFreq.sector_frequency.annual_frequency_per_1k) {
      findings.push(`Sector analysis: "${topFreq.title}" occurs at ${topFreq.sector_frequency.annual_frequency_per_1k} incidents/1k orgs/year in the ${report.industry_sector} sector (${topFreq.sector_frequency.sector_percentile ?? '?'}th percentile).`);
    }
  }

  // Threat actor groups
  const groupNames: string[] = [];
  threats.forEach(t => {
    t.attack_groups.forEach(g => {
      if (g.group_names) groupNames.push(...(g.group_names as string[]));
    });
  });
  const uniqueGroups = [...new Set(groupNames)].slice(0, 4);
  if (uniqueGroups.length > 0)
    findings.push(`Known threat actor groups associated with these threats: ${uniqueGroups.join(', ')}.`);

  if (findings.length === 0)
    findings.push('No threats have been analysed yet. Run enrichment and ML scoring to generate intelligent findings.');

  return (
    <ul className="space-y-2">
      {findings.map((f, i) => (
        <li key={i} className="flex gap-2 text-sm text-gray-700">
          <span className="mt-0.5 text-blue-500 flex-shrink-0">•</span>
          <span>{f}</span>
        </li>
      ))}
    </ul>
  );
}

// Deduplicated executive recommendations across all threats
function ExecRecommendations({ threats }: { threats: ThreatReportItem[] }) {
  const seen = new Set<string>();
  const recs: Array<{ title?: string; description: string; priority: string }> = [];
  const priorityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  threats.forEach(t => {
    t.recommendations.forEach(r => {
      const key = r.description.trim().toLowerCase().slice(0, 80);
      if (!seen.has(key)) {
        seen.add(key);
        recs.push({ title: r.title, description: r.description, priority: r.priority });
      }
    });
    // Inline recommendation from threat
    if (t.recommendation) {
      const key = t.recommendation.trim().toLowerCase().slice(0, 80);
      if (!seen.has(key)) {
        seen.add(key);
        recs.push({ description: t.recommendation, priority: t.severity });
      }
    }
  });
  recs.sort((a, b) => (priorityOrder[a.priority?.toLowerCase()] ?? 9) - (priorityOrder[b.priority?.toLowerCase()] ?? 9));

  if (recs.length === 0) return <p className="text-sm text-gray-500 italic">No recommendations recorded yet.</p>;

  return (
    <ol className="space-y-2">
      {recs.slice(0, 12).map((r, i) => (
        <li key={i} className="flex gap-3 text-sm">
          <span className="font-bold text-gray-400 flex-shrink-0 w-5">{i + 1}.</span>
          <span className="text-gray-700">{r.title ? <><strong>{r.title}:</strong> {r.description}</> : r.description}</span>
        </li>
      ))}
    </ol>
  );
}

// ─── Technical per-threat card ──────────────────────────────────────────────

function ThreatCard({ threat, index }: { threat: ThreatReportItem; index: number }) {
  const sev = (threat.severity || 'medium').toLowerCase();
  const borderClass = SEV_BORDER[sev] ?? 'border-l-gray-300';

  const hasNvd    = threat.intel_sources.includes('nvd');
  const hasCisa   = threat.intel_sources.includes('cisa_kev') || !!threat.cve_data?.cisa_kev;
  const hasOtx    = threat.intel_sources.some(s => s.startsWith('otx'));
  const hasGithub = threat.intel_sources.includes('github_poc');
  const hasSector = threat.intel_sources.includes('sector_freq');
  const hasGroups = threat.intel_sources.includes('attack_group');

  return (
    <div className={`bg-white rounded-lg border border-gray-200 border-l-4 ${borderClass} p-6 print:break-inside-avoid`}>
      {/* Threat header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 text-gray-500 text-sm font-bold flex items-center justify-center">
            {index + 1}
          </span>
          <div>
            <h3 className="text-lg font-bold text-gray-900">{threat.title}</h3>
            {threat.catalogue_key && (
              <span className="text-xs text-gray-400 font-mono">catalogue: {threat.catalogue_key}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <SeverityBadge sev={sev} />
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border font-medium ${
            threat.status === 'mitigated' ? 'bg-green-50 text-green-700 border-green-200' :
            threat.status === 'at_risk'   ? 'bg-red-50 text-red-700 border-red-200' :
            threat.status === 'in_review' ? 'bg-blue-50 text-blue-700 border-blue-200' :
            'bg-gray-50 text-gray-600 border-gray-200'
          }`}>
            {threat.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      {threat.description && (
        <p className="text-sm text-gray-600 mb-4 leading-relaxed">{threat.description}</p>
      )}

      {/* Risk Score + CVE row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        {/* ML Risk Score */}
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Activity className="w-3 h-3" /> ML Risk Score
          </p>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-bold text-gray-900">{threat.likelihood_score}</span>
            <span className="text-sm text-gray-500">/ 100</span>
            <SeverityBadge sev={threat.likelihood_label} />
          </div>
          <ScoreBar score={threat.likelihood_score} color={SEV_BAR[threat.likelihood_label] ?? 'bg-blue-500'} />
        </div>

        {/* CVE / CVSS */}
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Shield className="w-3 h-3" /> Vulnerability Data
          </p>
          {threat.cvss_score ? (
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-3xl font-bold text-gray-900">{threat.cvss_score}</span>
              <span className="text-sm text-gray-500">CVSS</span>
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">No CVSS score</p>
          )}
          {threat.cve_ids.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {threat.cve_ids.map(c => (
                <span key={c} className="text-xs font-mono bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded border border-blue-100">{c}</span>
              ))}
            </div>
          )}
          {hasCisa && (
            <span className="mt-1 inline-flex items-center text-xs text-red-600 font-semibold">
              ⚠ CISA KEV — actively exploited
            </span>
          )}
        </div>
      </div>

      {/* Intel source badges */}
      {threat.intel_sources.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Intel Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {hasNvd    && <span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100 font-medium">NVD</span>}
            {hasCisa   && <span className="text-xs px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-100 font-medium">CISA KEV</span>}
            {hasOtx    && <span className="text-xs px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-100 font-medium">AlienVault OTX</span>}
            {hasGithub && <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700 border border-gray-200 font-medium">GitHub PoC</span>}
            {hasSector && <span className="text-xs px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-100 font-medium">Sector Freq.</span>}
            {hasGroups && <span className="text-xs px-2 py-0.5 rounded bg-orange-50 text-orange-700 border border-orange-100 font-medium">ATT&CK Groups</span>}
          </div>
        </div>
      )}

      {/* ML Top Factors */}
      {threat.top_factors.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Cpu className="w-3 h-3" /> ML Likelihood Drivers
          </p>
          <div className="space-y-1.5">
            {threat.top_factors.slice(0, 5).map((f, i) => {
              const feat = f.feature ?? f.name ?? `factor_${i}`;
              const contrib = Math.abs(f.contribution ?? f.weight ?? 0);
              const pct = Math.min(100, contrib * 100);
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-44 truncate font-mono">{feat.replace(/_/g, ' ')}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-400 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-gray-400 w-12 text-right">{contrib.toFixed ? contrib.toFixed(3) : contrib}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Sector Frequency */}
      {hasSector && threat.sector_frequency.annual_frequency_per_1k != null && (
        <div className="mb-4 bg-teal-50 rounded-lg p-3 border border-teal-100">
          <p className="text-xs font-semibold text-teal-700 uppercase tracking-wide mb-1 flex items-center gap-1">
            <Globe className="w-3 h-3" /> Sector Frequency Analysis
          </p>
          <div className="grid grid-cols-3 gap-3 mt-2">
            <div>
              <p className="text-2xl font-bold text-teal-800">{threat.sector_frequency.annual_frequency_per_1k}</p>
              <p className="text-xs text-teal-600">incidents / 1k orgs / yr</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-teal-800">{threat.sector_frequency.sector_percentile ?? '—'}th</p>
              <p className="text-xs text-teal-600">percentile</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-teal-800">{threat.sector_frequency.relative_to_average ?? '—'}×</p>
              <p className="text-xs text-teal-600">vs cross-sector avg</p>
            </div>
          </div>
          {threat.sector_frequency.sector_display_name && (
            <p className="text-xs text-teal-500 mt-1">Sector: {threat.sector_frequency.sector_display_name}</p>
          )}
        </div>
      )}

      {/* Threat Actor Groups */}
      {threat.attack_groups.length > 0 && (threat.attack_groups[0]?.group_count ?? 0) > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Users className="w-3 h-3" /> Associated Threat Actor Groups
          </p>
          <div className="flex flex-wrap gap-2">
            {(threat.attack_groups[0]?.group_names ?? []).slice(0, 8).map((g: string, i: number) => (
              <span key={i} className="text-xs px-2 py-1 bg-orange-50 text-orange-800 rounded border border-orange-100 font-medium">
                {g}
              </span>
            ))}
            {(threat.attack_groups[0]?.group_count ?? 0) > 8 && (
              <span className="text-xs text-gray-400">+{(threat.attack_groups[0]?.group_count ?? 0) - 8} more</span>
            )}
          </div>
        </div>
      )}

      {/* ATT&CK Technique Mappings */}
      {threat.attack_mappings.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Target className="w-3 h-3" /> MITRE ATT&CK Mappings
          </p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-100">
                <th className="pb-1 font-medium w-24">Technique ID</th>
                <th className="pb-1 font-medium">Name</th>
                <th className="pb-1 font-medium w-32">Tactic</th>
                <th className="pb-1 font-medium w-16 text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {threat.attack_mappings.map((m, i) => (
                <tr key={i} className="border-b border-gray-50 last:border-0">
                  <td className="py-1.5 font-mono text-blue-600">{m.mitre_id}</td>
                  <td className="py-1.5 text-gray-700">{m.technique_name}</td>
                  <td className="py-1.5 text-gray-500">{m.tactic_shortname?.replace(/-/g, ' ')}</td>
                  <td className="py-1.5 text-right">
                    <span className={`font-semibold ${m.confidence_score >= 80 ? 'text-green-600' : m.confidence_score >= 60 ? 'text-yellow-600' : 'text-gray-400'}`}>
                      {m.confidence_score}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Kill Chains */}
      {threat.kill_chains.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <ChevronRight className="w-3 h-3" /> Kill Chain Scenarios
          </p>
          {threat.kill_chains.map((kc, ki) => (
            <div key={ki} className="mb-3 last:mb-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-semibold text-gray-800">{kc.scenario_name}</span>
                {kc.threat_actor && (
                  <span className="text-xs px-1.5 py-0.5 bg-red-50 text-red-700 rounded border border-red-100">{kc.threat_actor}</span>
                )}
              </div>
              <div className="relative">
                {/* Vertical connector line */}
                <div className="absolute left-3 top-4 bottom-0 w-px bg-gray-200" />
                <div className="space-y-3">
                  {kc.stages.map((s) => (
                    <div key={s.stage_number} className="relative flex gap-3 pl-8">
                      {/* Stage dot */}
                      <div className="absolute left-0 top-1.5 w-6 h-6 rounded-full bg-gray-200 text-gray-600 text-xs font-bold flex items-center justify-center flex-shrink-0 z-10">
                        {s.stage_number}
                      </div>
                      <div className="flex-1 bg-gray-50 rounded-md p-2.5 border border-gray-100">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-gray-700">{s.tactic_name}</span>
                          {s.mitre_id && (
                            <span className="text-xs font-mono text-blue-600 bg-blue-50 px-1 rounded">{s.mitre_id}</span>
                          )}
                          {s.technique_name && (
                            <span className="text-xs text-gray-500">— {s.technique_name}</span>
                          )}
                        </div>
                        {s.actor_behavior && (
                          <p className="text-xs text-gray-600 mb-1"><strong>Actor:</strong> {s.actor_behavior}</p>
                        )}
                        {s.detection_hint && (
                          <p className="text-xs text-green-700 bg-green-50 rounded px-2 py-1 border border-green-100">
                            <strong>Detect:</strong> {s.detection_hint}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      {(threat.recommendations.length > 0 || threat.recommendation) && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Recommendations
          </p>
          {threat.recommendation && (
            <p className="text-sm text-gray-700 mb-2 p-2 bg-blue-50 rounded border border-blue-100">{threat.recommendation}</p>
          )}
          {threat.recommendations.length > 0 && (
            <ul className="space-y-1.5">
              {threat.recommendations.map((r, ri) => (
                <li key={ri} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className={`mt-0.5 flex-shrink-0 text-xs font-bold px-1 py-0.5 rounded ${
                    r.priority?.toLowerCase() === 'critical' ? 'bg-red-100 text-red-700' :
                    r.priority?.toLowerCase() === 'high'     ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{r.priority?.toUpperCase() ?? 'MED'}</span>
                  <span>{r.title ? <><strong>{r.title}</strong> — {r.description}</> : r.description}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Report Page ───────────────────────────────────────────────────────

export default function AssessmentReportPage() {
  const params = useParams();
  const assessmentId = params.id as string;

  const [report, setReport]   = useState<AssessmentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAssessmentReport(assessmentId);
      setReport(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Failed to load report');
    } finally {
      setLoading(false);
    }
  }, [assessmentId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Building report…</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto py-24 text-center">
        <p className="text-red-600 mb-4">{error ?? 'Report not available.'}</p>
        <Link href={`/assessments/${assessmentId}`} className="text-blue-600 hover:underline">← Back to Assessment</Link>
      </div>
    );
  }

  const generated = new Date(report.generated_at).toLocaleString(undefined, {
    dateStyle: 'long', timeStyle: 'short',
  });

  return (
    <>
      {/* ── Print-only styles injected via style tag ────────────────── */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .print\\:break-inside-avoid { break-inside: avoid; }
          body { font-size: 12px; }
          .print-section { break-before: page; }
        }
      `}</style>

      <div className="min-h-screen bg-gray-50 print:bg-white">
        {/* ── Nav bar (screen only) ─────────────────────────────────── */}
        <div className="no-print sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          <Link
            href={`/assessments/${assessmentId}`}
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            Back to Assessment
          </Link>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Printer className="w-4 h-4" />
            Print / Export PDF
          </button>
        </div>

        <div className="max-w-5xl mx-auto px-6 py-8 print:px-4 print:py-4">

          {/* ═══════════════════════════════════════════════════════════
              REPORT HEADER
          ════════════════════════════════════════════════════════════ */}
          <div className="mb-8 pb-6 border-b-2 border-gray-200 flex items-start justify-between">
            <div>
              <p className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-1">Threat Risk Assessment Report</p>
              <h1 className="text-3xl font-extrabold text-gray-900 mb-1">{report.assessment_title}</h1>
              {report.assessment_description && (
                <p className="text-gray-500 text-sm max-w-2xl">{report.assessment_description}</p>
              )}
              <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-500">
                {report.industry_sector && (
                  <span className="flex items-center gap-1">
                    <Globe className="w-3.5 h-3.5" />
                    Sector: <strong className="text-gray-700 ml-1 capitalize">{report.industry_sector.replace(/_/g, ' ')}</strong>
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Shield className="w-3.5 h-3.5" />
                  Overall Impact: <strong className="text-gray-700 ml-1">{report.overall_impact}</strong>
                </span>
                <span className="flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5" />
                  {report.stats.total} threat{report.stats.total !== 1 ? 's' : ''} analysed
                </span>
              </div>
            </div>
            <div className="text-right text-xs text-gray-400 flex-shrink-0 ml-4">
              <p>Generated</p>
              <p className="font-medium text-gray-600">{generated}</p>
              <p className="mt-1">CONFIDENTIAL</p>
            </div>
          </div>

          {/* ═══════════════════════════════════════════════════════════
              SECTION 1 — EXECUTIVE SUMMARY (CISO)
          ════════════════════════════════════════════════════════════ */}
          <section className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 mb-1 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600" />
              Section 1 — Executive Summary
            </h2>
            <p className="text-sm text-gray-500 mb-6">For CISO and senior leadership. High-level risk posture, top threats, and strategic recommendations.</p>

            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Critical', value: report.stats.critical, color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
                { label: 'High',     value: report.stats.high,     color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
                { label: 'At Risk',  value: report.stats.at_risk,  color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200' },
                { label: 'Mitigated',value: report.stats.mitigated,color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
              ].map(c => (
                <div key={c.label} className={`rounded-xl border ${c.border} ${c.bg} p-4 text-center`}>
                  <p className={`text-4xl font-extrabold ${c.color}`}>{c.value}</p>
                  <p className="text-sm text-gray-600 mt-1">{c.label}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
              {/* Severity distribution */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide">Severity Distribution</h3>
                <SeverityDistBar stats={report.stats} />
                <div className="mt-4 pt-3 border-t border-gray-100 grid grid-cols-2 gap-2 text-xs text-gray-500">
                  <span>Enriched: <strong className="text-gray-700">{report.stats.enriched}</strong></span>
                  <span>With exploits: <strong className="text-gray-700">{report.stats.with_exploits}</strong></span>
                  <span>With kill chains: <strong className="text-gray-700">{report.stats.with_kill_chains}</strong></span>
                  <span>Total threats: <strong className="text-gray-700">{report.stats.total}</strong></span>
                </div>
              </div>

              {/* Key findings */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" /> Key Findings
                </h3>
                <KeyFindings report={report} />
              </div>
            </div>

            {/* Top 5 risks table */}
            {report.top_risks.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
                <h3 className="text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide">Top Risks by ML Score</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                      <th className="pb-2 font-medium">#</th>
                      <th className="pb-2 font-medium">Threat</th>
                      <th className="pb-2 font-medium">Severity</th>
                      <th className="pb-2 font-medium text-right">ML Score</th>
                      <th className="pb-2 font-medium text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_risks.map((t, i) => (
                      <tr key={t.id} className="border-b border-gray-50 last:border-0">
                        <td className="py-2 text-gray-400 font-mono">{i + 1}</td>
                        <td className="py-2 font-medium text-gray-800">{t.title}</td>
                        <td className="py-2"><SeverityBadge sev={t.severity} /></td>
                        <td className="py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${SEV_BAR[t.likelihood_label] ?? 'bg-blue-400'}`} style={{ width: `${t.likelihood_score}%` }} />
                            </div>
                            <span className="font-bold text-gray-800 w-8 text-right">{t.likelihood_score}</span>
                          </div>
                        </td>
                        <td className="py-2 text-right text-xs text-gray-500 capitalize">{t.status.replace('_', ' ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Executive recommendations */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-bold text-gray-700 mb-4 uppercase tracking-wide flex items-center gap-1">
                <CheckCircle className="w-4 h-4 text-green-500" /> Strategic Recommendations
              </h3>
              <ExecRecommendations threats={report.threats} />
            </div>
          </section>

          {/* ═══════════════════════════════════════════════════════════
              SECTION 2 — TECHNICAL ANALYSIS (SOC / Engineering)
          ════════════════════════════════════════════════════════════ */}
          <section className="print-section">
            <h2 className="text-xl font-bold text-gray-900 mb-1 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-indigo-600" />
              Section 2 — Technical Analysis
            </h2>
            <p className="text-sm text-gray-500 mb-6">For SOC analysts, architects, and engineering teams. Full per-threat breakdown including CVE data, ML drivers, ATT&CK mappings, and kill chains.</p>

            {report.threats.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No threats recorded for this assessment yet.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {report.threats.map((t, i) => (
                  <ThreatCard key={t.id} threat={t} index={i} />
                ))}
              </div>
            )}
          </section>

          {/* Footer */}
          <div className="mt-12 pt-6 border-t border-gray-200 text-center text-xs text-gray-400 print:mt-4">
            <p>CONFIDENTIAL — Threat Risk Assessment Platform &nbsp;|&nbsp; Generated {generated}</p>
            <p className="mt-1">This report contains sensitive security information. Handle in accordance with your information classification policy.</p>
          </div>

        </div>
      </div>
    </>
  );
}
