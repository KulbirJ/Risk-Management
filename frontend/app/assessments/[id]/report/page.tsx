'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowLeft, Printer, Shield, AlertTriangle, CheckCircle, TrendingUp, Globe, Cpu, Users, Target, ChevronRight, Activity, BookOpen, Info, Eye, Zap, BarChart3, FileWarning } from 'lucide-react';
import apiClient from '../../../../lib/api-client';
import type { AssessmentReport, ThreatReportItem } from '../../../../lib/types';

// ─── Severity helpers ───────────────────────────────────────────────────────

const SEV_COLOUR: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-800',
  high:     'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-800',
  medium:   'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800',
  low:      'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800',
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

// Inline explainer for AI/ML terms — renders a subtle info tooltip
function Explainer({ term, tip }: { term: string; tip: string }) {
  return (
    <span className="group relative inline-flex items-center gap-1 cursor-help">
      <span className="underline decoration-dotted underline-offset-2 decoration-gray-400 dark:decoration-gray-500">{term}</span>
      <Info className="w-3 h-3 text-gray-400 dark:text-gray-500 flex-shrink-0" />
      <span className="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-2.5 rounded-lg bg-gray-900 dark:bg-gray-700 text-white text-xs leading-relaxed shadow-lg z-50 pointer-events-none">
        {tip}
      </span>
    </span>
  );
}

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
      <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      {label && <span className="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">{label}</span>}
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
          <span className="w-16 text-sm text-gray-600 dark:text-gray-400">{b.label}</span>
          <div className="flex-1 h-4 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${b.color}`}
              style={{ width: `${(b.count / total) * 100}%` }}
            />
          </div>
          <span className="w-6 text-sm font-semibold text-gray-700 dark:text-gray-300 text-right">{b.count}</span>
        </div>
      ))}
    </div>
  );
}

// Auto-generated executive key-findings bullets — written for a non-technical audience
function KeyFindings({ report }: { report: AssessmentReport }) {
  const { stats, threats } = report;
  const findings: Array<{ icon: string; text: string; severity: 'critical' | 'warning' | 'info' | 'success' }> = [];

  if (stats.critical > 0)
    findings.push({ icon: '🔴', severity: 'critical', text: `${stats.critical} critical issue${stats.critical > 1 ? 's' : ''} found that need${stats.critical === 1 ? 's' : ''} immediate attention — these pose the highest risk to your organization.` });
  if (stats.at_risk > 0)
    findings.push({ icon: '⚠️', severity: 'warning', text: `${stats.at_risk} risk${stats.at_risk > 1 ? 's are' : ' is'} being actively monitored in the risk register, meaning they are known but not yet fully resolved.` });
  if (stats.with_exploits > 0)
    findings.push({ icon: '💻', severity: 'critical', text: `${stats.with_exploits} threat${stats.with_exploits > 1 ? 's have' : ' has'} publicly available exploit code, which means attackers already have tools to take advantage of these weaknesses.` });
  if (stats.with_kill_chains > 0)
    findings.push({ icon: '🔗', severity: 'warning', text: `${stats.with_kill_chains} threat${stats.with_kill_chains > 1 ? 's have' : ' has'} AI-modeled attack scenarios that map how an attacker could progress step-by-step — useful for security drills and planning.` });
  if (stats.mitigated > 0)
    findings.push({ icon: '✅', severity: 'success', text: `${stats.mitigated} threat${stats.mitigated > 1 ? 's have' : ' has'} been successfully addressed. Ongoing monitoring is recommended to ensure they stay resolved.` });

  // Sector frequency finding
  const withSectorFreq = threats.filter(t => t.sector_frequency && Object.keys(t.sector_frequency).length > 0);
  if (withSectorFreq.length > 0 && report.industry_sector) {
    const topFreq = withSectorFreq.sort((a, b) => (b.sector_frequency.annual_frequency_per_1k ?? 0) - (a.sector_frequency.annual_frequency_per_1k ?? 0))[0];
    if (topFreq.sector_frequency.annual_frequency_per_1k) {
      findings.push({ icon: '📊', severity: 'info', text: `Industry data shows "${topFreq.title}" affects ${topFreq.sector_frequency.annual_frequency_per_1k} out of every 1,000 organizations per year in the ${report.industry_sector.replace(/_/g, ' ')} sector — placing it in the ${topFreq.sector_frequency.sector_percentile ?? '?'}th percentile of threats for your industry.` });
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
    findings.push({ icon: '👤', severity: 'warning', text: `Known hacker groups linked to these threats include: ${uniqueGroups.join(', ')}. These are tracked globally by security organizations.` });

  if (findings.length === 0)
    findings.push({ icon: 'ℹ️', severity: 'info', text: 'No threats have been analysed yet. Run the assessment to generate findings.' });

  const sevColors = {
    critical: 'border-l-red-400 bg-red-50/50 dark:bg-red-950/20',
    warning: 'border-l-amber-400 bg-amber-50/50 dark:bg-amber-950/20',
    info: 'border-l-blue-400 bg-blue-50/50 dark:bg-blue-950/20',
    success: 'border-l-green-400 bg-green-50/50 dark:bg-green-950/20',
  };

  return (
    <div className="space-y-2">
      {findings.map((f, i) => (
        <div key={i} className={`flex gap-3 text-sm text-gray-700 dark:text-gray-300 p-3 rounded-lg border-l-4 ${sevColors[f.severity]}`}>
          <span className="text-base flex-shrink-0">{f.icon}</span>
          <span className="leading-relaxed">{f.text}</span>
        </div>
      ))}
    </div>
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

  if (recs.length === 0) return <p className="text-sm text-gray-500 dark:text-gray-400 italic">No recommendations recorded yet.</p>;

  return (
    <ol className="space-y-2">
      {recs.slice(0, 12).map((r, i) => (
        <li key={i} className="flex gap-3 text-sm">
          <span className="font-bold text-gray-400 dark:text-gray-500 flex-shrink-0 w-5">{i + 1}.</span>
          <span className="text-gray-700 dark:text-gray-300">{r.title ? <><strong className="text-gray-900 dark:text-white">{r.title}:</strong> {r.description}</> : r.description}</span>
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
    <div className={`bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 border-l-4 ${borderClass} p-6 print:break-inside-avoid`}>
      {/* Threat header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-3">
          <span className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-sm font-bold flex items-center justify-center">
            {index + 1}
          </span>
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">{threat.title}</h3>
            {threat.catalogue_key && (
              <span className="text-xs text-gray-400 dark:text-gray-500 font-mono">catalogue: {threat.catalogue_key}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <SeverityBadge sev={sev} />
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border font-medium ${
            threat.status === 'mitigated' ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800' :
            threat.status === 'at_risk'   ? 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800' :
            threat.status === 'in_review' ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800' :
            'bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:border-gray-600'
          }`}>
            {threat.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      {threat.description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 leading-relaxed">{threat.description}</p>
      )}

      {/* Risk Score + CVE row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        {/* Risk Score */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Activity className="w-3 h-3" />
            <Explainer term="Risk Score" tip="A score from 0–100 calculated by our AI model. It estimates how likely this threat is to be exploited based on multiple intelligence signals. Higher = more urgent." />
          </p>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-bold text-gray-900 dark:text-white">{threat.likelihood_score}</span>
            <span className="text-sm text-gray-500 dark:text-gray-400">/ 100</span>
            <SeverityBadge sev={threat.likelihood_label} />
          </div>
          <ScoreBar score={threat.likelihood_score} color={SEV_BAR[threat.likelihood_label] ?? 'bg-blue-500'} />
        </div>

        {/* CVE / CVSS */}
        <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Shield className="w-3 h-3" />
            <Explainer term="Vulnerability Data" tip="CVE is a unique ID for a known software weakness. CVSS is a severity score (0–10) assigned by the security community. Higher CVSS = more severe vulnerability." />
          </p>
          {threat.cvss_score ? (
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-3xl font-bold text-gray-900 dark:text-white">{threat.cvss_score}</span>
              <span className="text-sm text-gray-500 dark:text-gray-400">CVSS</span>
            </div>
          ) : (
            <p className="text-sm text-gray-400 dark:text-gray-500 italic">No CVSS score</p>
          )}
          {threat.cve_ids.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {threat.cve_ids.map(c => (
                <span key={c} className="text-xs font-mono bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 px-1.5 py-0.5 rounded border border-blue-100 dark:border-blue-800">{c}</span>
              ))}
            </div>
          )}
          {hasCisa && (
            <span className="mt-1 inline-flex items-center text-xs text-red-600 dark:text-red-400 font-semibold">
              ⚠ Actively exploited in the wild (CISA confirmed)
            </span>
          )}
        </div>
      </div>

      {/* Intel source badges */}
      {threat.intel_sources.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
            <Explainer term="Intelligence Sources" tip="These are the security databases and feeds that provided data for this threat. More sources = higher confidence in the analysis." />
          </p>
          <div className="flex flex-wrap gap-1.5">
            {hasNvd    && <span className="text-xs px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border border-blue-100 dark:border-blue-800 font-medium">NVD</span>}
            {hasCisa   && <span className="text-xs px-2 py-0.5 rounded bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-100 dark:border-red-800 font-medium">CISA KEV</span>}
            {hasOtx    && <span className="text-xs px-2 py-0.5 rounded bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 border border-purple-100 dark:border-purple-800 font-medium">AlienVault OTX</span>}
            {hasGithub && <span className="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 font-medium">Public Exploit</span>}
            {hasSector && <span className="text-xs px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400 border border-teal-100 dark:border-teal-800 font-medium">Industry Data</span>}
            {hasGroups && <span className="text-xs px-2 py-0.5 rounded bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-100 dark:border-orange-800 font-medium">Threat Groups</span>}
          </div>
        </div>
      )}

      {/* ML Top Factors */}
      {threat.top_factors.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Cpu className="w-3 h-3" />
            <Explainer term="What's Driving This Score" tip="These are the factors our AI model weighted most heavily when calculating the risk score. Each bar shows how much influence that factor had on the final number." />
          </p>
          <div className="space-y-1.5">
            {threat.top_factors.slice(0, 5).map((f, i) => {
              const feat = f.feature ?? f.name ?? `factor_${i}`;
              const contrib = Math.abs(f.contribution ?? f.weight ?? 0);
              const pct = Math.min(100, contrib * 100);
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 dark:text-gray-400 w-44 truncate">{feat.replace(/_/g, ' ')}</span>
                  <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-400 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-gray-400 dark:text-gray-500 w-12 text-right">{contrib.toFixed ? contrib.toFixed(3) : contrib}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Sector Frequency */}
      {hasSector && threat.sector_frequency.annual_frequency_per_1k != null && (
        <div className="mb-4 bg-teal-50 dark:bg-teal-900/20 rounded-lg p-3 border border-teal-100 dark:border-teal-800">
          <p className="text-xs font-semibold text-teal-700 dark:text-teal-400 uppercase tracking-wide mb-1 flex items-center gap-1">
            <Globe className="w-3 h-3" />
            <Explainer term="How Common Is This in Your Industry?" tip="This data compares how frequently this type of threat occurs in your industry sector vs. other sectors, based on annual reports from Verizon, IBM, and ENISA." />
          </p>
          <div className="grid grid-cols-3 gap-3 mt-2">
            <div>
              <p className="text-2xl font-bold text-teal-800 dark:text-teal-300">{threat.sector_frequency.annual_frequency_per_1k}</p>
              <p className="text-xs text-teal-600 dark:text-teal-400">incidents / 1,000 orgs / year</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-teal-800 dark:text-teal-300">{threat.sector_frequency.sector_percentile ?? '—'}th</p>
              <p className="text-xs text-teal-600 dark:text-teal-400">percentile in sector</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-teal-800 dark:text-teal-300">{threat.sector_frequency.relative_to_average ?? '—'}×</p>
              <p className="text-xs text-teal-600 dark:text-teal-400">vs. cross-sector avg</p>
            </div>
          </div>
          {threat.sector_frequency.sector_display_name && (
            <p className="text-xs text-teal-500 dark:text-teal-500 mt-1">Sector: {threat.sector_frequency.sector_display_name}</p>
          )}
        </div>
      )}

      {/* Threat Actor Groups */}
      {threat.attack_groups.length > 0 && (threat.attack_groups[0]?.group_count ?? 0) > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Users className="w-3 h-3" />
            <Explainer term="Known Threat Actor Groups" tip="These are named hacker groups (tracked by global security organizations) that are known to use techniques associated with this threat. Their involvement signals a higher level of sophistication." />
          </p>
          <div className="flex flex-wrap gap-2">
            {(threat.attack_groups[0]?.group_names ?? []).slice(0, 8).map((g: string, i: number) => (
              <span key={i} className="text-xs px-2 py-1 bg-orange-50 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400 rounded border border-orange-100 dark:border-orange-800 font-medium">
                {g}
              </span>
            ))}
            {(threat.attack_groups[0]?.group_count ?? 0) > 8 && (
              <span className="text-xs text-gray-400 dark:text-gray-500">+{(threat.attack_groups[0]?.group_count ?? 0) - 8} more</span>
            )}
          </div>
        </div>
      )}

      {/* ATT&CK Technique Mappings */}
      {threat.attack_mappings.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <Target className="w-3 h-3" />
            <Explainer term="Attack Technique Mappings" tip="MITRE ATT&CK is a global knowledge base of real-world cyberattack techniques. These mappings show which specific attack methods are associated with this threat and our confidence level for each." />
          </p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700">
                <th className="pb-1 font-medium w-24">Technique</th>
                <th className="pb-1 font-medium">Name</th>
                <th className="pb-1 font-medium w-32">Category</th>
                <th className="pb-1 font-medium w-16 text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {threat.attack_mappings.map((m, i) => (
                <tr key={i} className="border-b border-gray-50 dark:border-gray-700/50 last:border-0">
                  <td className="py-1.5 font-mono text-blue-600 dark:text-blue-400">{m.mitre_id}</td>
                  <td className="py-1.5 text-gray-700 dark:text-gray-300">{m.technique_name}</td>
                  <td className="py-1.5 text-gray-500 dark:text-gray-400">{m.tactic_shortname?.replace(/-/g, ' ')}</td>
                  <td className="py-1.5 text-right">
                    <span className={`font-semibold ${m.confidence_score >= 80 ? 'text-green-600 dark:text-green-400' : m.confidence_score >= 60 ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-400 dark:text-gray-500'}`}>
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
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <ChevronRight className="w-3 h-3" />
            <Explainer term="Attack Scenario (Kill Chain)" tip="An AI-generated step-by-step model showing how an attacker could exploit this threat from start to finish. Each stage shows what the attacker does and how your team can detect or stop them." />
          </p>
          {threat.kill_chains.map((kc, ki) => (
            <div key={ki} className="mb-3 last:mb-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">{kc.scenario_name}</span>
                {kc.threat_actor && (
                  <span className="text-xs px-1.5 py-0.5 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded border border-red-100 dark:border-red-800">{kc.threat_actor}</span>
                )}
              </div>
              <div className="relative">
                <div className="absolute left-3 top-4 bottom-0 w-px bg-gray-200 dark:bg-gray-700" />
                <div className="space-y-3">
                  {kc.stages.map((s) => (
                    <div key={s.stage_number} className="relative flex gap-3 pl-8">
                      <div className="absolute left-0 top-1.5 w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs font-bold flex items-center justify-center flex-shrink-0 z-10">
                        {s.stage_number}
                      </div>
                      <div className="flex-1 bg-gray-50 dark:bg-gray-900/50 rounded-md p-2.5 border border-gray-100 dark:border-gray-700">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{s.tactic_name}</span>
                          {s.mitre_id && (
                            <span className="text-xs font-mono text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-1 rounded">{s.mitre_id}</span>
                          )}
                          {s.technique_name && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">— {s.technique_name}</span>
                          )}
                        </div>
                        {s.actor_behavior && (
                          <p className="text-xs text-gray-600 dark:text-gray-400 mb-1"><strong>What the attacker does:</strong> {s.actor_behavior}</p>
                        )}
                        {s.detection_hint && (
                          <p className="text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded px-2 py-1 border border-green-100 dark:border-green-800">
                            <strong>How to detect it:</strong> {s.detection_hint}
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
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Recommended Actions
          </p>
          {threat.recommendation && (
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-100 dark:border-blue-800">{threat.recommendation}</p>
          )}
          {threat.recommendations.length > 0 && (
            <ul className="space-y-1.5">
              {threat.recommendations.map((r, ri) => (
                <li key={ri} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <span className={`mt-0.5 flex-shrink-0 text-xs font-bold px-1 py-0.5 rounded ${
                    r.priority?.toLowerCase() === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400' :
                    r.priority?.toLowerCase() === 'high'     ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400' :
                    'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                  }`}>{r.priority?.toUpperCase() ?? 'MED'}</span>
                  <span>{r.title ? <><strong className="text-gray-900 dark:text-white">{r.title}</strong> — {r.description}</> : r.description}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Definitions Appendix ──────────────────────────────────────────────────

const GLOSSARY: Array<{ term: string; category: string; definition: string }> = [
  // Risk & Threat concepts
  {
    term: 'Threat',
    category: 'Risk',
    definition:
      'Any circumstance or event with the potential to adversely impact organisational operations, assets, or individuals through unauthorised access, destruction, disclosure, modification of information, or denial of service.',
  },
  {
    term: 'Risk',
    category: 'Risk',
    definition:
      'The potential for loss or harm resulting from the likelihood of a threat exploiting a vulnerability, combined with the impact that exploitation would cause.',
  },
  {
    term: 'Severity',
    category: 'Risk',
    definition:
      'A composite rating (Low / Medium / High / Critical) computed from the intersection of a threat\'s Likelihood and Impact scores. Critical indicates maximum urgency.',
  },
  {
    term: 'Likelihood',
    category: 'Risk',
    definition:
      'The probability that a given threat will be exploited within a defined period. Rated Low, Medium, High, or Critical based on threat intelligence, historical data, and ML analysis.',
  },
  {
    term: 'Impact',
    category: 'Risk',
    definition:
      'The potential business and operational consequences if a threat is successfully exploited — considering data loss, financial damage, regulatory penalties, and reputational harm.',
  },
  {
    term: 'Residual Risk',
    category: 'Risk',
    definition:
      'The risk that remains after all mitigation controls have been applied. Residual risk is accepted, transferred (e.g. via insurance), or subject to further treatment.',
  },
  {
    term: 'Active Risk',
    category: 'Risk',
    definition:
      'A threat that has been escalated to the risk register because it cannot be immediately fully mitigated. Active risks are tracked with an owner, review cycle, and estimated persistence.',
  },
  // ML & Scoring
  {
    term: 'Risk Score (AI-Powered)',
    category: 'ML & Scoring',
    definition:
      'A number from 0 to 100 that represents how likely a threat is to be exploited. This score is calculated by our AI model, which analyzes multiple data points including vulnerability severity, whether exploits exist in the wild, how common the threat is in your industry, and known attacker group activity. Scores 75+ are Critical, 50–74 High, 25–49 Medium, and below 25 Low.',
  },
  {
    term: 'Score Drivers (What\'s Behind the Number)',
    category: 'ML & Scoring',
    definition:
      'The individual factors that most influenced a threat\'s Risk Score — for example, the severity of the vulnerability, whether a public exploit exists, or how common this threat is in your sector. Each driver shows its relative weight, giving you transparency into why a particular score was assigned.',
  },
  {
    term: 'Feature Vector',
    category: 'ML & Scoring',
    definition:
      'A technical term for the standardized set of data points fed into the AI model. Think of it as a "profile card" for each threat that combines all relevant signals (severity, exploit availability, industry frequency, etc.) into a format the model can process.',
  },
  {
    term: 'Estimated Persistence',
    category: 'ML & Scoring',
    definition:
      'A prediction (in days) of how long a risk is likely to remain unresolved, based on your organization\'s historical remediation speed, industry benchmarks, and the severity of the threat. This helps teams plan resources and set realistic timelines.',
  },
  // Intelligence & Enrichment
  {
    term: 'Enrichment (Automated Intelligence Gathering)',
    category: 'Intelligence',
    definition:
      'The automated process where the platform gathers additional information about each threat from multiple security databases and feeds. This adds context like severity scores, whether the threat is being actively exploited, and how common it is in your industry — all without manual research.',
  },
  {
    term: 'NVD (National Vulnerability Database)',
    category: 'Intelligence',
    definition:
      'The U.S. government repository of vulnerability management data (NIST). Provides CVSS scores, CWE classifications, and remediation guidance for publicly disclosed CVEs.',
  },
  {
    term: 'CVE (Common Vulnerabilities and Exposures)',
    category: 'Intelligence',
    definition:
      'A globally unique identifier assigned to a publicly disclosed cybersecurity vulnerability. Format: CVE-YYYY-NNNNN. Maintained by MITRE and published in the NVD.',
  },
  {
    term: 'CVSS (Common Vulnerability Scoring System)',
    category: 'Intelligence',
    definition:
      'An open standard for rating the severity of software vulnerabilities on a scale of 0.0–10.0. A score ≥9.0 is Critical; 7.0–8.9 High; 4.0–6.9 Medium; <4.0 Low.',
  },
  {
    term: 'CISA KEV',
    category: 'Intelligence',
    definition:
      'CISA\'s Known Exploited Vulnerabilities catalogue — a list of CVEs that have been actively exploited in the wild. US federal agencies must patch KEV entries within mandated timeframes. Presence on KEV is a strong signal of elevated real-world risk.',
  },
  {
    term: 'AlienVault OTX',
    category: 'Intelligence',
    definition:
      'Open Threat Exchange — a global threat intelligence sharing community operated by AT&T Cybersecurity. OTX Pulses are crowd-sourced threat reports linking indicators of compromise (IoCs) and TTPs to specific threats or CVEs.',
  },
  {
    term: 'GitHub PoC (Proof of Concept)',
    category: 'Intelligence',
    definition:
      'Publicly available exploit code or proof-of-concept repositories hosted on GitHub that demonstrate how a specific vulnerability can be exploited. Existence of a public PoC significantly raises a threat\'s exploitability rating.',
  },
  {
    term: 'Sector Frequency',
    category: 'Intelligence',
    definition:
      'The annualised rate of a specific threat type occurring across organisations in a given industry sector, expressed as incidents per 1,000 organisations per year. Derived from Verizon DBIR, IBM X-Force, and ENISA annual reports. Used to contextualise whether a threat is above or below the sector average.',
  },
  {
    term: 'Sector Percentile',
    category: 'Intelligence',
    definition:
      'The relative position of a threat\'s incident frequency compared to all other threat types in the same sector. A 90th-percentile threat occurs more frequently than 90% of all threats tracked in that sector.',
  },
  // ATT&CK & Kill Chain
  {
    term: 'MITRE ATT&CK',
    category: 'ATT&CK & Kill Chain',
    definition:
      'A globally accessible, curated knowledge base of adversary tactics, techniques, and procedures (TTPs) based on real-world observations. The Enterprise matrix covers 14 tactics and 700+ techniques across Windows, macOS, Linux, cloud, and network environments.',
  },
  {
    term: 'Tactic',
    category: 'ATT&CK & Kill Chain',
    definition:
      'The adversary\'s tactical goal — the "why" of an ATT&CK technique. The 14 Enterprise tactics range from Reconnaissance through to Impact, following the logical progression of an attack.',
  },
  {
    term: 'Technique',
    category: 'ATT&CK & Kill Chain',
    definition:
      'A specific method an adversary uses to achieve a tactical goal. Identified by a MITRE ID (e.g. T1566 — Phishing). Sub-techniques (e.g. T1566.001) refine the parent technique further.',
  },
  {
    term: 'ATT&CK Technique Mapping',
    category: 'ATT&CK & Kill Chain',
    definition:
      'An association between a threat in this assessment and one or more MITRE ATT&CK techniques. Mappings can be AI-suggested (auto-mapped) or manually curated by analysts. Each mapping carries a confidence score (0–100%).',
  },
  {
    term: 'Kill Chain (Attack Scenario)',
    category: 'ATT&CK & Kill Chain',
    definition:
      'An AI-generated step-by-step model showing how an attacker could progress from initial entry to full impact. Each stage shows the attacker\'s likely actions and provides detection tips for defenders. Think of it as a "game plan" that shows both the offense (attacker) and defense (your team) perspective. Based on the Lockheed Martin Cyber Kill Chain® and MITRE ATT&CK framework.',
  },
  {
    term: 'Kill Chain Stage',
    category: 'ATT&CK & Kill Chain',
    definition:
      'An individual step within a kill chain scenario — e.g. "Stage 2: Persistence via Scheduled Task (T1053.005)". Each stage describes what the attacker does (Actor Behavior) and how defenders can detect or disrupt it (Detection Hint).',
  },
  {
    term: 'Threat Actor / APT Group',
    category: 'ATT&CK & Kill Chain',
    definition:
      'A named adversary group tracked by the security community, catalogued in MITRE ATT&CK as an Intrusion Set. Examples include APT29 (Cozy Bear, Russia), FIN7 (financially motivated), and Lazarus Group (North Korea). Groups are associated with the techniques they are known to use.',
  },
  {
    term: 'Intrusion Set (STIX)',
    category: 'ATT&CK & Kill Chain',
    definition:
      'The STIX 2.1 object type used in MITRE\'s CTI (Cyber Threat Intelligence) repository to represent a threat actor group and their attributed campaigns, tools, and techniques.',
  },
  // Platform
  {
    term: 'Assessment',
    category: 'Platform',
    definition:
      'A scoped risk evaluation exercise tied to a specific system, project, or organisational unit. An assessment contains one or more identified threats, associated evidence, recommendations, and an overall risk posture.',
  },
  {
    term: 'Threat Catalogue',
    category: 'Platform',
    definition:
      'A pre-defined library of canonical threat types (e.g. ransomware, social engineering, denial of service) with standard descriptions, default likelihood/impact ratings, and sector frequency mappings. Threats in an assessment reference catalogue entries via a catalogue_key.',
  },
  {
    term: 'Recommendation',
    category: 'Platform',
    definition:
      'A specific mitigation, remediation, or compensating control action assigned to a threat or assessment. Recommendations carry a priority, status (open / in progress / done), and optionally an owner and target date.',
  },
  {
    term: 'Evidence',
    category: 'Platform',
    definition:
      'Uploaded supporting artefacts (architecture diagrams, vulnerability scan reports, policy documents, etc.) attached to an assessment or individual threat. Evidence is parsed and fed into AI enrichment to improve the accuracy of threat analysis.',
  },
  {
    term: 'Audit Log',
    category: 'Platform',
    definition:
      'An immutable, append-only record of every significant action taken within the platform (e.g. threat created, risk accepted, recommendation updated). Used for compliance evidence, change tracking, and forensic investigation.',
  },
  {
    term: 'Tenant',
    category: 'Platform',
    definition:
      'A logically isolated organisational unit within the platform. All assessments, threats, users, and intelligence data are scoped to a single tenant, ensuring data segregation in multi-organisation deployments.',
  },
];

const GLOSSARY_CATEGORIES = [...new Set(GLOSSARY.map(g => g.category))];

function DefinitionsAppendix() {
  return (
    <section className="print-section mt-12">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
        <BookOpen className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        Appendix — Definitions & Glossary
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        Plain-language definitions for all terms, ratings, and data sources used in this report.
      </p>

      {GLOSSARY_CATEGORIES.map(cat => (
        <div key={cat} className="mb-8">
          <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-3 pb-1 border-b border-gray-100 dark:border-gray-700">
            {cat}
          </h3>
          <dl className="space-y-4">
            {GLOSSARY.filter(g => g.category === cat).map(g => (
              <div key={g.term} className="grid grid-cols-1 sm:grid-cols-4 gap-1 sm:gap-4">
                <dt className="sm:col-span-1 text-sm font-semibold text-gray-800 dark:text-gray-200 pt-0.5">{g.term}</dt>
                <dd className="sm:col-span-3 text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{g.definition}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}

      {/* Severity rating reference table */}
      <div className="mb-8">
        <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-3 pb-1 border-b border-gray-100 dark:border-gray-700">
          Severity & Score Reference
        </h3>
        <table className="w-full text-sm border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr className="text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <th className="px-4 py-2">Rating</th>
              <th className="px-4 py-2">Risk Score Range</th>
              <th className="px-4 py-2">CVSS Equivalent</th>
              <th className="px-4 py-2">Recommended Response Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            <tr className="dark:bg-gray-800/50">
              <td className="px-4 py-2"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-800 uppercase">Critical</span></td>
              <td className="px-4 py-2 font-mono text-gray-700 dark:text-gray-300">75 – 100</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">9.0 – 10.0</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">Immediate — within 24–72 hours</td>
            </tr>
            <tr className="dark:bg-gray-800/50">
              <td className="px-4 py-2"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-800 uppercase">High</span></td>
              <td className="px-4 py-2 font-mono text-gray-700 dark:text-gray-300">50 – 74</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">7.0 – 8.9</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">Short-term — within 7–14 days</td>
            </tr>
            <tr className="dark:bg-gray-800/50">
              <td className="px-4 py-2"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800 border border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-800 uppercase">Medium</span></td>
              <td className="px-4 py-2 font-mono text-gray-700 dark:text-gray-300">25 – 49</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">4.0 – 6.9</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">Planned — within 30–60 days</td>
            </tr>
            <tr className="dark:bg-gray-800/50">
              <td className="px-4 py-2"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-200 dark:bg-green-900/40 dark:text-green-300 dark:border-green-800 uppercase">Low</span></td>
              <td className="px-4 py-2 font-mono text-gray-700 dark:text-gray-300">0 – 24</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">0.1 – 3.9</td>
              <td className="px-4 py-2 text-gray-600 dark:text-gray-400">Backlog — next review cycle</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Sources & References */}
      <div>
        <h3 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-3 pb-1 border-b border-gray-100 dark:border-gray-700">
          Data Sources & References
        </h3>
        <ul className="space-y-1.5 text-sm text-gray-600 dark:text-gray-400">
          <li><strong className="text-gray-800 dark:text-gray-200">MITRE ATT&CK Enterprise:</strong> attack.mitre.org — global knowledge base of real-world cyberattack techniques</li>
          <li><strong className="text-gray-800 dark:text-gray-200">NVD (NIST):</strong> nvd.nist.gov — U.S. government vulnerability database with severity scores</li>
          <li><strong className="text-gray-800 dark:text-gray-200">CISA KEV:</strong> cisa.gov/known-exploited-vulnerabilities-catalog — confirmed actively exploited vulnerabilities</li>
          <li><strong className="text-gray-800 dark:text-gray-200">AlienVault OTX:</strong> otx.alienvault.com — community-driven threat intelligence reports</li>
          <li><strong className="text-gray-800 dark:text-gray-200">GitHub Advisory / PoC:</strong> github.com/search — publicly available exploit code repositories</li>
          <li><strong className="text-gray-800 dark:text-gray-200">Verizon DBIR, IBM X-Force, ENISA:</strong> Annual industry reports providing sector-specific threat frequency data</li>
          <li><strong className="text-gray-800 dark:text-gray-200">STIX 2.1 / TAXII 2.1:</strong> International standards for sharing structured threat intelligence</li>
        </ul>
      </div>
    </section>
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
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">Building report…</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto py-24 text-center">
        <p className="text-red-600 dark:text-red-400 mb-4">{error ?? 'Report not available.'}</p>
        <Link href={`/assessments/${assessmentId}`} className="text-blue-600 dark:text-blue-400 hover:underline">← Back to Assessment</Link>
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

      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 print:bg-white">
        {/* ── Nav bar (screen only) ─────────────────────────────────── */}
        <div className="no-print sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-3 flex items-center justify-between">
          <Link
            href={`/assessments/${assessmentId}`}
            className="inline-flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            Back to Assessment
          </Link>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Printer className="w-4 h-4" />
            Print / Export PDF
          </button>
        </div>

        <div className="max-w-5xl mx-auto px-6 py-8 print:px-4 print:py-4">

          {/* ═══════════════════════════════════════════════════════════
              BRANDED REPORT HEADER
          ════════════════════════════════════════════════════════════ */}
          <div className="mb-10 pb-8 border-b-2 border-gray-200 dark:border-gray-700">
            {/* Logo + confidentiality banner */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Image src="/logo.png" alt="EdgeVision" width={160} height={40} className="h-10 w-auto" />
              </div>
              <div className="text-right text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
                <p className="font-semibold text-red-500 dark:text-red-400 text-sm mb-0.5">CONFIDENTIAL</p>
                <p>Generated {generated}</p>
              </div>
            </div>

            {/* Report title area */}
            <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-cyan-900 rounded-2xl p-8 text-white mb-6 print:bg-gray-900">
              <p className="text-xs font-bold text-cyan-300 uppercase tracking-widest mb-2 flex items-center gap-2">
                <Shield className="w-4 h-4" />
                Threat Risk Assessment Report
              </p>
              <h1 className="text-3xl font-extrabold mb-2">{report.assessment_title}</h1>
              {report.assessment_description && (
                <p className="text-gray-300 text-sm max-w-2xl leading-relaxed">{report.assessment_description}</p>
              )}
              <div className="flex flex-wrap gap-5 mt-4 text-sm text-gray-300">
                {report.industry_sector && (
                  <span className="flex items-center gap-1.5">
                    <Globe className="w-4 h-4 text-cyan-400" />
                    Sector: <strong className="text-white ml-1 capitalize">{report.industry_sector.replace(/_/g, ' ')}</strong>
                  </span>
                )}
                <span className="flex items-center gap-1.5">
                  <Shield className="w-4 h-4 text-cyan-400" />
                  Overall Impact: <strong className="text-white ml-1">{report.overall_impact}</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <TrendingUp className="w-4 h-4 text-cyan-400" />
                  {report.stats.total} threat{report.stats.total !== 1 ? 's' : ''} analysed
                </span>
              </div>
            </div>

            {/* Quick risk summary — the "at a glance" strip for executives */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { label: 'Total Threats', value: report.stats.total, icon: Eye, color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-50 dark:bg-gray-800', border: 'border-gray-200 dark:border-gray-700' },
                { label: 'Critical', value: report.stats.critical, icon: AlertTriangle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/30', border: 'border-red-200 dark:border-red-800' },
                { label: 'High', value: report.stats.high, icon: Zap, color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-950/30', border: 'border-orange-200 dark:border-orange-800' },
                { label: 'Active Risks', value: report.stats.at_risk, icon: FileWarning, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-950/30', border: 'border-purple-200 dark:border-purple-800' },
                { label: 'Resolved', value: report.stats.mitigated, icon: CheckCircle, color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-950/30', border: 'border-green-200 dark:border-green-800' },
              ].map(c => (
                <div key={c.label} className={`rounded-xl border ${c.border} ${c.bg} p-4 text-center`}>
                  <c.icon className={`w-5 h-5 mx-auto mb-1.5 ${c.color}`} />
                  <p className={`text-3xl font-extrabold ${c.color}`}>{c.value}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-medium">{c.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* ═══════════════════════════════════════════════════════════
              SECTION 1 — EXECUTIVE SUMMARY (CISO)
          ════════════════════════════════════════════════════════════ */}
          <section className="mb-12">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              Section 1 — Executive Summary
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">A high-level overview for leadership. Understand your risk posture at a glance without technical complexity.</p>

            {/* Stat cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Critical', value: report.stats.critical, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/30', border: 'border-red-200 dark:border-red-800' },
                { label: 'High',     value: report.stats.high,     color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-950/30', border: 'border-orange-200 dark:border-orange-800' },
                { label: 'Active Risks',  value: report.stats.at_risk,  color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-950/30', border: 'border-purple-200 dark:border-purple-800' },
                { label: 'Resolved',value: report.stats.mitigated,color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-950/30', border: 'border-green-200 dark:border-green-800' },
              ].map(c => (
                <div key={c.label} className={`rounded-xl border ${c.border} ${c.bg} p-4 text-center`}>
                  <p className={`text-4xl font-extrabold ${c.color}`}>{c.value}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{c.label}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
              {/* Severity distribution */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4 uppercase tracking-wide">Threat Severity Breakdown</h3>
                <SeverityDistBar stats={report.stats} />
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>AI-Enriched: <strong className="text-gray-700 dark:text-gray-300">{report.stats.enriched}</strong></span>
                  <span>Public exploits found: <strong className="text-gray-700 dark:text-gray-300">{report.stats.with_exploits}</strong></span>
                  <span>Attack scenarios modeled: <strong className="text-gray-700 dark:text-gray-300">{report.stats.with_kill_chains}</strong></span>
                  <span>Total threats: <strong className="text-gray-700 dark:text-gray-300">{report.stats.total}</strong></span>
                </div>
              </div>

              {/* Key findings */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4 uppercase tracking-wide flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" /> Key Findings
                </h3>
                <KeyFindings report={report} />
              </div>
            </div>

            {/* Top 5 risks table */}
            {report.top_risks.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 mb-6">
                <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-1 uppercase tracking-wide">
                  Top Risks by <Explainer term="AI Risk Score" tip="Each threat is scored 0–100 by our AI model based on vulnerability severity, exploit availability, industry frequency data, and known attacker activity. Higher scores indicate greater urgency." />
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">These are the threats requiring the most immediate attention based on automated analysis of multiple risk factors.</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700">
                      <th className="pb-2 font-medium">#</th>
                      <th className="pb-2 font-medium">Threat</th>
                      <th className="pb-2 font-medium">Severity</th>
                      <th className="pb-2 font-medium text-right">Risk Score</th>
                      <th className="pb-2 font-medium text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_risks.map((t, i) => (
                      <tr key={t.id} className="border-b border-gray-50 dark:border-gray-700/50 last:border-0">
                        <td className="py-2 text-gray-400 dark:text-gray-500 font-mono">{i + 1}</td>
                        <td className="py-2 font-medium text-gray-800 dark:text-gray-200">{t.title}</td>
                        <td className="py-2"><SeverityBadge sev={t.severity} /></td>
                        <td className="py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-20 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${SEV_BAR[t.likelihood_label] ?? 'bg-blue-400'}`} style={{ width: `${t.likelihood_score}%` }} />
                            </div>
                            <span className="font-bold text-gray-800 dark:text-gray-200 w-8 text-right">{t.likelihood_score}</span>
                          </div>
                        </td>
                        <td className="py-2 text-right text-xs text-gray-500 dark:text-gray-400 capitalize">{t.status.replace('_', ' ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Executive recommendations */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <h3 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4 uppercase tracking-wide flex items-center gap-1">
                <CheckCircle className="w-4 h-4 text-green-500" /> Recommended Actions
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">Prioritized list of actions to reduce your organization&apos;s risk exposure, ordered from most to least urgent.</p>
              <ExecRecommendations threats={report.threats} />
            </div>
          </section>

          {/* ═══════════════════════════════════════════════════════════
              SECTION 2 — TECHNICAL ANALYSIS (SOC / Engineering)
          ════════════════════════════════════════════════════════════ */}
          <section className="print-section">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              Section 2 — Detailed Threat Analysis
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">In-depth breakdown of each identified threat. Includes risk scoring, vulnerability data, attack technique mappings, and recommended actions. Hover over underlined terms for definitions.</p>

            {report.threats.length === 0 ? (
              <div className="text-center py-16 text-gray-400 dark:text-gray-500">
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

          {/* ═══════════════════════════════════════════════════════════
              APPENDIX — DEFINITIONS & GLOSSARY
          ════════════════════════════════════════════════════════════ */}
          <DefinitionsAppendix />

          {/* Footer */}
          <div className="mt-12 pt-6 border-t border-gray-200 dark:border-gray-700 text-center text-xs text-gray-400 dark:text-gray-500 print:mt-4">
            <p>CONFIDENTIAL — EdgeVision Risk Intelligence &amp; Compliance Platform &nbsp;|&nbsp; Generated {generated}</p>
            <p className="mt-1">This report contains sensitive security information. Handle in accordance with your information classification policy.</p>
          </div>

        </div>
      </div>
    </>
  );
}
