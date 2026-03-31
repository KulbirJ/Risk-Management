'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Package, ChevronLeft, ChevronRight } from 'lucide-react';
import Layout from '../../../components/Layout';
import apiClient from '../../../lib/api-client';
import { SupplyChainAssessmentCreate } from '../../../lib/types';

const LEVELS = ['Low', 'Medium', 'High'] as const;

export default function NewSupplyChainAssessmentPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Step 0 — Basics
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [scope, setScope] = useState('');
  const [industrySector, setIndustrySector] = useState('');

  // Step 1 — Technology Sensitivity
  const [techSensitivity, setTechSensitivity] = useState<'Low' | 'Medium' | 'High'>('Medium');
  const [techFunction, setTechFunction] = useState('');
  const [dataClassification, setDataClassification] = useState('');
  const [ecosystemImportance, setEcosystemImportance] = useState('');

  // Step 3 — Deployment Risk
  const [deployEnv, setDeployEnv] = useState('');
  const [cyberDefense, setCyberDefense] = useState<'Low' | 'Medium' | 'High'>('Medium');
  const [deployNotes, setDeployNotes] = useState('');

  const canProceed = () => {
    if (step === 1) return title.trim().length > 0;
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload: SupplyChainAssessmentCreate = {
        title,
        description: description || undefined,
        scope: scope || undefined,
        industry_sector: industrySector || undefined,
        technology_sensitivity: techSensitivity,
        technology_function: techFunction || undefined,
        data_classification: dataClassification || undefined,
        ecosystem_importance: ecosystemImportance || undefined,
        deployment_environment: deployEnv || undefined,
        cyber_defense_level: cyberDefense,
        deployment_notes: deployNotes || undefined,
      };
      const created = await apiClient.createSupplyChainAssessment(payload);
      router.push(`/supply-chain/${created.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create assessment.');
    } finally {
      setSaving(false);
    }
  };

  const STEPS = [
    { num: 1, label: 'Basics' },
    { num: 2, label: 'Step 1 — Technology Sensitivity' },
    { num: 3, label: 'Step 3 — Deployment Risk' },
  ];

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/supply-chain')}
            className="text-sm text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400 flex items-center gap-1 mb-3"
          >
            <ChevronLeft className="w-4 h-4" /> Back to Supply Chain
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Package className="w-6 h-6 text-indigo-600" />
            New Supply Chain Assessment
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            CCCS ITSAP.10.070 — 3 step risk evaluation
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-1 mb-8">
          {STEPS.map((s) => (
            <button
              key={s.num}
              onClick={() => setStep(s.num)}
              className={`flex-1 py-2 text-xs font-medium rounded-lg text-center transition-colors ${
                step === s.num
                  ? 'bg-indigo-600 text-white'
                  : step > s.num
                  ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Step 1 — Basics */}
          {step === 1 && (
            <div className="space-y-5">
              <Field label="Title *" value={title} onChange={setTitle} placeholder="e.g. Q2 2026 — Log4j Supply Chain Review" />
              <Field label="Description" value={description} onChange={setDescription} multiline placeholder="Purpose and objectives of this assessment" />
              <Field label="Scope" value={scope} onChange={setScope} multiline placeholder="Products, services, and suppliers in scope" />
              <SelectField label="Industry Sector" value={industrySector} onChange={setIndustrySector} options={['', 'finance', 'healthcare', 'government', 'energy', 'technology', 'telecommunications', 'retail', 'manufacturing', 'other']} />
            </div>
          )}

          {/* Step 2 — Technology Sensitivity (CCCS Step 1) */}
          {step === 2 && (
            <div className="space-y-5">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>CCCS Step 1:</strong> How sensitive is the technology being assessed?
                Higher sensitivity means a supply chain compromise has greater impact on the organization.
              </p>
              <LevelField label="Technology Sensitivity" value={techSensitivity} onChange={(v) => setTechSensitivity(v as typeof techSensitivity)} />
              <Field label="Technology Function" value={techFunction} onChange={setTechFunction} placeholder="e.g. Encryption, Authentication, Data Storage" />
              <SelectField label="Data Classification" value={dataClassification} onChange={setDataClassification} options={['', 'Public', 'Internal', 'Confidential', 'Secret', 'Top Secret']} />
              <Field label="Ecosystem Importance" value={ecosystemImportance} onChange={setEcosystemImportance} placeholder="How critical is this tech to the broader ecosystem? (e.g. widely adopted, niche)" />
            </div>
          )}

          {/* Step 3 — Deployment Risk (CCCS Step 3) */}
          {step === 3 && (
            <div className="space-y-5">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>CCCS Step 3:</strong> How well can you defend & detect threats once the technology is deployed?
                Higher cyber defence capability lowers deployment risk.
              </p>
              <LevelField label="Cyber Defence Capability" value={cyberDefense} onChange={(v) => setCyberDefense(v as typeof cyberDefense)} />
              <Field label="Deployment Environment" value={deployEnv} onChange={setDeployEnv} placeholder="e.g. On-premises, Cloud (AWS), Hybrid, Air-gapped" />
              <Field label="Deployment Notes" value={deployNotes} onChange={setDeployNotes} multiline placeholder="Additional context about mitigations, network segmentation, monitoring" />
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={() => setStep(Math.max(1, step - 1))}
              disabled={step === 1}
              className="inline-flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" /> Previous
            </button>
            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep(step + 1)}
                disabled={!canProceed()}
                className="inline-flex items-center gap-1 px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={saving || !canProceed()}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {saving ? 'Creating…' : 'Create Assessment'}
              </button>
            )}
          </div>
        </form>
      </div>
    </Layout>
  );
}

/* ── helpers ────────────────────────────────────────────────── */

function Field({
  label,
  value,
  onChange,
  placeholder,
  multiline,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  const cls =
    'w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white px-3 py-2 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500';
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      {multiline ? (
        <textarea rows={3} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={`${cls} mt-1`} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={`${cls} mt-1`} />
      )}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o || '— Select —'}
          </option>
        ))}
      </select>
    </label>
  );
}

function LevelField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const levels = ['Low', 'Medium', 'High'];
  const colours: Record<string, string> = {
    Low: 'bg-green-600',
    Medium: 'bg-yellow-500',
    High: 'bg-red-600',
  };
  return (
    <div>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
      <div className="flex gap-2 mt-1">
        {levels.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => onChange(l)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              value === l
                ? `${colours[l]} text-white`
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}
