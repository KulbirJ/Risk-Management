'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Package, AlertTriangle, Users, Layers, TrendingUp } from 'lucide-react';
import Layout from '../../components/Layout';
import apiClient from '../../lib/api-client';
import { SupplyChainAssessment } from '../../lib/types';
import { format } from 'date-fns';

const RISK_COLOURS: Record<string, string> = {
  Low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  Medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  High: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  Critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const STATUS_COLOURS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  in_review: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  archived: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
};

export default function SupplyChainPage() {
  const [assessments, setAssessments] = useState<SupplyChainAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const items = await apiClient.listSupplyChainAssessments();
        setAssessments(items);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to load supply chain assessments.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const totalVendors = assessments.reduce((s, a) => s + (a.vendor_count ?? 0), 0);
  const totalDeps = assessments.reduce((s, a) => s + (a.dependency_count ?? 0), 0);
  const criticalDeps = assessments.reduce((s, a) => s + (a.critical_dependency_count ?? 0), 0);

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Package className="w-7 h-7 text-indigo-600" />
              Supply Chain Risk
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              CCCS ITSAP.10.070 — Technology Sensitivity · Supplier Confidence · Deployment Risk
            </p>
          </div>
          <Link
            href="/supply-chain/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Assessment
          </Link>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Assessments', value: assessments.length, icon: Package, colour: 'text-indigo-600' },
            { label: 'Vendors', value: totalVendors, icon: Users, colour: 'text-blue-600' },
            { label: 'Dependencies', value: totalDeps, icon: Layers, colour: 'text-violet-600' },
            { label: 'Critical / High Deps', value: criticalDeps, icon: AlertTriangle, colour: 'text-red-600' },
          ].map(({ label, value, icon: Icon, colour }) => (
            <div
              key={label}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5"
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-8 h-8 ${colour}`} />
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-3" />
                <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded w-1/2 mb-6" />
                <div className="h-8 bg-gray-100 dark:bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        ) : assessments.length === 0 ? (
          <div className="text-center py-20">
            <Package className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400 mb-6">No supply chain assessments yet.</p>
            <Link
              href="/supply-chain/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
              Start your first assessment
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {assessments.map((a) => (
              <Link
                key={a.id}
                href={`/supply-chain/${a.id}`}
                className="block bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <h2 className="font-semibold text-gray-900 dark:text-white text-sm leading-snug line-clamp-2 flex-1 pr-2">
                    {a.title}
                  </h2>
                  <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOURS[a.status] ?? ''}`}>
                    {a.status.replace('_', ' ')}
                  </span>
                </div>
                {a.overall_risk_level && (
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="w-3.5 h-3.5 text-gray-400" />
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RISK_COLOURS[a.overall_risk_level] ?? ''}`}>
                      {a.overall_risk_level} Risk
                    </span>
                    {a.overall_risk_score !== undefined && (
                      <span className="text-xs text-gray-400">({a.overall_risk_score}/100)</span>
                    )}
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  {[
                    { label: 'Vendors', val: a.vendor_count ?? 0 },
                    { label: 'Deps', val: a.dependency_count ?? 0 },
                    { label: 'Critical', val: a.critical_dependency_count ?? 0 },
                  ].map(({ label, val }) => (
                    <div key={label} className="bg-gray-50 dark:bg-gray-700/50 rounded-lg py-2">
                      <p className="font-bold text-gray-900 dark:text-white">{val}</p>
                      <p className="text-gray-500 dark:text-gray-400">{label}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-xs text-gray-400">
                  {format(new Date(a.created_at), 'MMM d, yyyy')}
                  {a.industry_sector ? ` · ${a.industry_sector}` : ''}
                </p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
