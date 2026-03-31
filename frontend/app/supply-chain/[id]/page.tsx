'use client';

import { useEffect, useState, useRef, ChangeEvent } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  Package, ChevronLeft, Users, Layers, AlertTriangle, RefreshCw,
  Plus, Trash2, Upload, Shield, TrendingUp, Zap,
} from 'lucide-react';
import Layout from '../../../components/Layout';
import apiClient from '../../../lib/api-client';
import {
  SupplyChainAssessment,
  SupplyChainVendor,
  SupplyChainDependency,
  SupplyChainVendorCreate,
  SupplyChainDependencyCreate,
  SCRiskScoreResponse,
} from '../../../lib/types';
import { format } from 'date-fns';

/* ── colour helpers ──────────────────────────────────────────────────────── */

const RISK_COLOURS: Record<string, string> = {
  Low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  Medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  High: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  Critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const CONF_COLOURS: Record<string, string> = {
  High: 'text-green-600 dark:text-green-400',
  Medium: 'text-yellow-600 dark:text-yellow-400',
  Low: 'text-red-600 dark:text-red-400',
};

type Tab = 'overview' | 'vendors' | 'dependencies' | 'sbom';

export default function SupplyChainDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();

  const [assessment, setAssessment] = useState<SupplyChainAssessment | null>(null);
  const [vendors, setVendors] = useState<SupplyChainVendor[]>([]);
  const [deps, setDeps] = useState<SupplyChainDependency[]>([]);
  const [tab, setTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoreResult, setScoreResult] = useState<SCRiskScoreResponse | null>(null);
  const [scoring, setScoring] = useState(false);
  const [enriching, setEnriching] = useState(false);

  // Vendor add form
  const [showVendorForm, setShowVendorForm] = useState(false);
  const [vName, setVName] = useState('');
  const [vCountry, setVCountry] = useState('');
  const [vType, setVType] = useState('');
  const [vFoci, setVFoci] = useState<'Low'|'Medium'|'High'>('Low');
  const [vGeo, setVGeo] = useState<'Low'|'Medium'|'High'>('Low');
  const [vBiz, setVBiz] = useState<'Low'|'Medium'|'High'>('Low');
  const [vDp, setVDp] = useState<'Low'|'Medium'|'High'>('Medium');
  const [vVuln, setVVuln] = useState<'Low'|'Medium'|'High'>('Medium');
  const [vSec, setVSec] = useState<'Low'|'Medium'|'High'>('Medium');

  // Dependency add form
  const [showDepForm, setShowDepForm] = useState(false);
  const [dName, setDName] = useState('');
  const [dVersion, setDVersion] = useState('');
  const [dPkgType, setDPkgType] = useState('');
  const [dCves, setDCves] = useState('');

  const sbomRef = useRef<HTMLInputElement>(null);

  /* ── load data ────────────────────────────────────────────────────── */

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      try {
        const [a, v, d] = await Promise.all([
          apiClient.getSupplyChainAssessment(id),
          apiClient.listSupplyChainVendors(id),
          apiClient.listSupplyChainDependencies(id),
        ]);
        setAssessment(a);
        setVendors(v);
        setDeps(d);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load assessment.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  /* ── actions ──────────────────────────────────────────────────────── */

  const recalculate = async () => {
    if (!id) return;
    setScoring(true);
    try {
      const result = await apiClient.recalculateSupplyChainScore(id);
      setScoreResult(result);
      setAssessment((prev) =>
        prev ? { ...prev, overall_risk_score: result.overall_risk_score, overall_risk_level: result.overall_risk_level as SupplyChainAssessment['overall_risk_level'] } : prev,
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Scoring failed.');
    } finally {
      setScoring(false);
    }
  };

  const enrichDeps = async () => {
    if (!id) return;
    setEnriching(true);
    try {
      const result = await apiClient.enrichSupplyChainDependencies(id);
      if (result.errors.length) {
        setError(`Enrichment: ${result.errors[0]}`);
      }
      // reload deps
      const updated = await apiClient.listSupplyChainDependencies(id);
      setDeps(updated);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Enrichment failed.');
    } finally {
      setEnriching(false);
    }
  };

  const addVendor = async () => {
    if (!id || !vName.trim()) return;
    try {
      const payload: SupplyChainVendorCreate = {
        assessment_id: id,
        name: vName,
        country_of_origin: vCountry || undefined,
        vendor_type: vType || undefined,
        foci_risk: vFoci,
        geopolitical_risk: vGeo,
        business_practices_risk: vBiz,
        data_protection_maturity: vDp,
        vuln_mgmt_maturity: vVuln,
        security_policies_maturity: vSec,
      };
      const created = await apiClient.createSupplyChainVendor(id, payload);
      setVendors((prev) => [...prev, created]);
      setShowVendorForm(false);
      resetVendorForm();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to add vendor.');
    }
  };

  const resetVendorForm = () => {
    setVName(''); setVCountry(''); setVType('');
    setVFoci('Low'); setVGeo('Low'); setVBiz('Low');
    setVDp('Medium'); setVVuln('Medium'); setVSec('Medium');
  };

  const deleteVendor = async (vendorId: string) => {
    if (!id) return;
    await apiClient.deleteSupplyChainVendor(id, vendorId);
    setVendors((prev) => prev.filter((v) => v.id !== vendorId));
  };

  const addDep = async () => {
    if (!id || !dName.trim()) return;
    try {
      const payload: SupplyChainDependencyCreate = {
        assessment_id: id,
        name: dName,
        version: dVersion || undefined,
        package_type: dPkgType || undefined,
        cve_ids: dCves ? dCves.split(',').map((c) => c.trim()).filter(Boolean) : [],
      };
      const created = await apiClient.createSupplyChainDependency(id, payload);
      setDeps((prev) => [...prev, created]);
      setShowDepForm(false);
      setDName(''); setDVersion(''); setDPkgType(''); setDCves('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to add dependency.');
    }
  };

  const handleSBOM = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !id) return;
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      const fmt = json.bomFormat ? 'cyclonedx' : json.spdxVersion ? 'spdx' : 'cyclonedx';
      const result = await apiClient.parseSBOM(id, json, fmt);
      if (result.components.length > 0) {
        const created = await apiClient.bulkCreateSupplyChainDependencies(
          id,
          result.components.map((c) => ({ ...c, assessment_id: id })),
        );
        setDeps((prev) => [...prev, ...created]);
      }
      if (result.warnings.length) {
        setError(`SBOM warnings: ${result.warnings.join('; ')}`);
      }
      setAssessment((prev) => prev ? { ...prev, sbom_uploaded: true, sbom_format: fmt } : prev);
    } catch (err: any) {
      setError('Invalid SBOM file. Ensure it is a valid CycloneDX or SPDX JSON document.');
    }
  };

  /* ── render ───────────────────────────────────────────────────────── */

  if (loading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 py-12">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
            <div className="h-4 bg-gray-100 dark:bg-gray-700 rounded w-1/2" />
            <div className="h-64 bg-gray-100 dark:bg-gray-700 rounded" />
          </div>
        </div>
      </Layout>
    );
  }

  if (!assessment) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 py-12 text-center text-gray-500 dark:text-gray-400">
          Assessment not found.
        </div>
      </Layout>
    );
  }

  const TABS: { key: Tab; label: string; icon: typeof Package }[] = [
    { key: 'overview', label: 'Overview', icon: TrendingUp },
    { key: 'vendors', label: `Vendors (${vendors.length})`, icon: Users },
    { key: 'dependencies', label: `Dependencies (${deps.length})`, icon: Layers },
    { key: 'sbom', label: 'SBOM Upload', icon: Upload },
  ];

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <button
          onClick={() => router.push('/supply-chain')}
          className="text-sm text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400 flex items-center gap-1 mb-4"
        >
          <ChevronLeft className="w-4 h-4" /> Back
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-indigo-600" />
              {assessment.title}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              Created {format(new Date(assessment.created_at), 'MMM d, yyyy')}
              {assessment.industry_sector ? ` · ${assessment.industry_sector}` : ''}
            </p>
          </div>
          <button
            onClick={recalculate}
            disabled={scoring}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${scoring ? 'animate-spin' : ''}`} />
            {scoring ? 'Scoring…' : 'Recalculate Risk'}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">×</button>
          </div>
        )}

        {/* Score banner */}
        {assessment.overall_risk_level && (
          <div className="mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Overall Risk</p>
              <span className={`text-lg font-bold px-3 py-0.5 rounded-full ${RISK_COLOURS[assessment.overall_risk_level] ?? ''}`}>
                {assessment.overall_risk_level}
              </span>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Score</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{assessment.overall_risk_score ?? '—'}<span className="text-sm text-gray-400">/100</span></p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Step 1 Sensitivity</p>
              <p className="font-semibold text-gray-900 dark:text-white">{assessment.technology_sensitivity}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Step 3 Defence</p>
              <p className="font-semibold text-gray-900 dark:text-white">{assessment.cyber_defense_level}</p>
            </div>
          </div>
        )}

        {/* Score detail panel */}
        {scoreResult && (
          <div className="mb-6 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-4 text-sm text-indigo-800 dark:text-indigo-200 space-y-1">
            <p><strong>Risk Score:</strong> {scoreResult.overall_risk_score}/100 ({scoreResult.overall_risk_level})</p>
            <p>Technology Sensitivity: {scoreResult.technology_sensitivity} · Avg Vendor Risk: {scoreResult.avg_supplier_risk}% · Deployment Risk: {scoreResult.deployment_risk}</p>
            <p>Critical/High dependencies: {scoreResult.dependency_critical_count}</p>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-6 overflow-x-auto">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === key
                  ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400 dark:border-indigo-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW TAB ──────────────────────────────────────────────── */}
        {tab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <InfoCard title="Description" text={assessment.description} />
            <InfoCard title="Scope" text={assessment.scope} />
            <InfoCard title="Technology Function" text={assessment.technology_function} />
            <InfoCard title="Data Classification" text={assessment.data_classification} />
            <InfoCard title="Ecosystem Importance" text={assessment.ecosystem_importance} />
            <InfoCard title="Deployment Environment" text={assessment.deployment_environment} />
            {assessment.deployment_notes && <InfoCard title="Deployment Notes" text={assessment.deployment_notes} />}
          </div>
        )}

        {/* ── VENDORS TAB ─────────────────────────────────────────────── */}
        {tab === 'vendors' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Step 2 — Supplier Confidence</h2>
              <button
                onClick={() => setShowVendorForm(!showVendorForm)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700"
              >
                <Plus className="w-4 h-4" /> Add Vendor
              </button>
            </div>

            {showVendorForm && (
              <div className="mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Input label="Vendor Name *" value={vName} onChange={setVName} />
                  <Input label="Country" value={vCountry} onChange={setVCountry} />
                  <Select label="Type" value={vType} onChange={setVType} options={['', 'oss', 'commercial', 'internal', 'saas', 'paas', 'iaas']} />
                </div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mt-2">CCCS Step 2 Sub-Factors</p>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <LevelPicker label="FOCI Risk" value={vFoci} onChange={setVFoci} />
                  <LevelPicker label="Geopolitical Risk" value={vGeo} onChange={setVGeo} />
                  <LevelPicker label="Business Practices Risk" value={vBiz} onChange={setVBiz} />
                  <LevelPicker label="Data Protection" value={vDp} onChange={setVDp} />
                  <LevelPicker label="Vuln Mgmt" value={vVuln} onChange={setVVuln} />
                  <LevelPicker label="Security Policies" value={vSec} onChange={setVSec} />
                </div>
                <div className="flex gap-2 justify-end">
                  <button onClick={() => { setShowVendorForm(false); resetVendorForm(); }} className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">Cancel</button>
                  <button onClick={addVendor} disabled={!vName.trim()} className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">Save Vendor</button>
                </div>
              </div>
            )}

            {vendors.length === 0 ? (
              <Empty text="No vendors yet. Add one to start the Step 2 assessment." />
            ) : (
              <div className="space-y-3">
                {vendors.map((v) => (
                  <div key={v.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 dark:text-white text-sm">{v.name}</p>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {v.country_of_origin && <span>{v.country_of_origin}</span>}
                        {v.vendor_type && <span>{v.vendor_type}</span>}
                        <span>FOCI: {v.foci_risk}</span>
                        <span>Geo: {v.geopolitical_risk}</span>
                        <span>Biz: {v.business_practices_risk}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 shrink-0 ml-4">
                      {v.supplier_confidence_level && (
                        <div className="text-center">
                          <p className="text-xs text-gray-400">Confidence</p>
                          <p className={`font-bold text-sm ${CONF_COLOURS[v.supplier_confidence_level] ?? ''}`}>
                            {v.supplier_confidence_level}
                          </p>
                        </div>
                      )}
                      {v.supplier_risk_score !== undefined && (
                        <div className="text-center">
                          <p className="text-xs text-gray-400">Score</p>
                          <p className="font-bold text-sm text-gray-900 dark:text-white">{v.supplier_risk_score}</p>
                        </div>
                      )}
                      <button
                        onClick={() => deleteVendor(v.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500 rounded"
                        title="Delete vendor"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── DEPENDENCIES TAB ────────────────────────────────────────── */}
        {tab === 'dependencies' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Software Dependencies</h2>
              <div className="flex gap-2">
                <button
                  onClick={enrichDeps}
                  disabled={enriching}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 text-white text-sm hover:bg-violet-700 disabled:opacity-50"
                >
                  <Zap className={`w-4 h-4 ${enriching ? 'animate-spin' : ''}`} />
                  {enriching ? 'Enriching…' : 'ML Enrich'}
                </button>
                <button
                  onClick={() => setShowDepForm(!showDepForm)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700"
                >
                  <Plus className="w-4 h-4" /> Add
                </button>
              </div>
            </div>

            {showDepForm && (
              <div className="mb-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Input label="Package Name *" value={dName} onChange={setDName} />
                  <Input label="Version" value={dVersion} onChange={setDVersion} />
                  <Select label="Type" value={dPkgType} onChange={setDPkgType} options={['', 'npm', 'pip', 'maven', 'nuget', 'gem', 'go', 'cargo', 'container']} />
                  <Input label="CVE IDs (comma sep.)" value={dCves} onChange={setDCves} />
                </div>
                <div className="flex gap-2 justify-end">
                  <button onClick={() => setShowDepForm(false)} className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">Cancel</button>
                  <button onClick={addDep} disabled={!dName.trim()} className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">Save</button>
                </div>
              </div>
            )}

            {deps.length === 0 ? (
              <Empty text="No dependencies yet. Add manually or upload an SBOM." />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                      <th className="py-2 pr-3">Package</th>
                      <th className="py-2 pr-3">Version</th>
                      <th className="py-2 pr-3">Type</th>
                      <th className="py-2 pr-3">CVEs</th>
                      <th className="py-2 pr-3">Risk</th>
                      <th className="py-2 pr-3">Score</th>
                      <th className="py-2 pr-3">KEV</th>
                      <th className="py-2 pr-3">PoC</th>
                      <th className="py-2 pr-3">ML</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {deps.map((d) => (
                      <tr key={d.id} className="text-gray-700 dark:text-gray-300">
                        <td className="py-2 pr-3 font-medium text-gray-900 dark:text-white whitespace-nowrap">{d.name}</td>
                        <td className="py-2 pr-3">{d.version ?? '—'}</td>
                        <td className="py-2 pr-3">{d.package_type ?? '—'}</td>
                        <td className="py-2 pr-3">{d.cve_ids.length > 0 ? d.cve_ids.join(', ') : '—'}</td>
                        <td className="py-2 pr-3">
                          {d.risk_level && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RISK_COLOURS[d.risk_level] ?? ''}`}>{d.risk_level}</span>}
                        </td>
                        <td className="py-2 pr-3">{d.risk_score ?? '—'}</td>
                        <td className="py-2 pr-3">{d.is_in_cisa_kev ? '⚠️' : '—'}</td>
                        <td className="py-2 pr-3">{d.has_public_poc ? '💥' : '—'}</td>
                        <td className="py-2 pr-3">{d.ml_enriched ? '✅' : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── SBOM TAB ────────────────────────────────────────────────── */}
        {tab === 'sbom' && (
          <div className="max-w-lg mx-auto text-center py-12">
            <Upload className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Upload SBOM</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Upload a CycloneDX or SPDX JSON file to automatically populate your dependency list.
            </p>
            {assessment.sbom_uploaded && (
              <p className="text-sm text-green-600 dark:text-green-400 mb-4">
                ✓ SBOM uploaded ({assessment.sbom_format})
              </p>
            )}
            <input ref={sbomRef} type="file" accept=".json" onChange={handleSBOM} className="hidden" />
            <button
              onClick={() => sbomRef.current?.click()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
            >
              <Upload className="w-4 h-4" />
              Choose JSON File
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}

/* ── shared sub-components ─────────────────────────────────────────── */

function InfoCard({ title, text }: { title: string; text?: string | null }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{title}</p>
      <p className="text-sm text-gray-900 dark:text-white">{text || '—'}</p>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">{text}</p>;
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
    </label>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        {options.map((o) => <option key={o} value={o}>{o || '— Select —'}</option>)}
      </select>
    </label>
  );
}

function LevelPicker({ label, value, onChange }: { label: string; value: string; onChange: (v: any) => void }) {
  const levels = ['Low', 'Medium', 'High'];
  const colours: Record<string, string> = { Low: 'bg-green-600', Medium: 'bg-yellow-500', High: 'bg-red-600' };
  return (
    <div>
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</span>
      <div className="flex gap-1 mt-1">
        {levels.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => onChange(l)}
            className={`flex-1 py-1 rounded text-xs font-medium transition-colors ${
              value === l ? `${colours[l]} text-white` : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
            }`}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}
