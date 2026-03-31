'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Search, LayoutGrid, List } from 'lucide-react';
import { Button } from '../../components/Button';
import { SkeletonTable } from '../../components/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { StatusBadge, SeverityBadge } from '../../components/Badge';
import { EmptyState } from '../../components/EmptyState';
import { Breadcrumb } from '../../components/Breadcrumb';
import apiClient from '../../lib/api-client';
import { Assessment } from '../../lib/types';
import { format } from 'date-fns';

type ViewMode = 'grid' | 'table';
type SortKey = 'title' | 'status' | 'overall_impact' | 'created_at';
type SortDir = 'asc' | 'desc';

export default function AssessmentsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(1);
  const perPage = 12;

  useEffect(() => {
    loadAssessments();
  }, [statusFilter]);

  const loadAssessments = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      const items = await apiClient.getAssessments(params);
      setAssessments(items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load assessments');
    } finally {
      setLoading(false);
    }
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sorted = [...assessments]
    .filter(
      (a) =>
        (a.title || '').toLowerCase().includes(filter.toLowerCase()) ||
        (a.description?.toLowerCase() || '').includes(filter.toLowerCase())
    )
    .sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      const va = (a as any)[sortKey] ?? '';
      const vb = (b as any)[sortKey] ?? '';
      if (sortKey === 'created_at') return dir * (new Date(va).getTime() - new Date(vb).getTime());
      return dir * String(va).localeCompare(String(vb));
    });

  const totalPages = Math.max(1, Math.ceil(sorted.length / perPage));
  const paginated = sorted.slice((page - 1) * perPage, page * perPage);

  useEffect(() => { setPage(1); }, [filter, statusFilter, sortKey, sortDir]);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="skeleton h-8 w-48 rounded" />
        <SkeletonTable rows={6} />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <Breadcrumb items={[{ label: 'Assessments' }]} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Assessments</h1>
          <p className="text-muted-foreground mt-1">Manage your threat risk assessments</p>
        </div>
        <Link href="/assessments/new">
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            New Assessment
          </Button>
        </Link>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Filters */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search assessments..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-background border border-border rounded-xl text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
          >
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="in_review">In Review</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>
          {/* View toggles */}
          <div className="flex rounded-xl border border-border overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 transition-colors ${viewMode === 'grid' ? 'bg-primary text-white' : 'bg-background text-muted-foreground hover:bg-muted'}`}
              aria-label="Grid view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-2 transition-colors ${viewMode === 'table' ? 'bg-primary text-white' : 'bg-background text-muted-foreground hover:bg-muted'}`}
              aria-label="Table view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      {paginated.length === 0 ? (
        <div className="bg-card rounded-xl border border-border">
          <EmptyState
            icon={filter ? 'search' : 'assessments'}
            title={filter ? 'No matching assessments' : 'No assessments yet'}
            description={filter ? 'Try adjusting your search or filters' : 'Create your first assessment to start identifying threats'}
            actionLabel={filter ? undefined : 'Create Assessment'}
            onAction={filter ? undefined : () => { window.location.href = '/assessments/new'; }}
          />
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {paginated.map((assessment) => (
            <Link
              key={assessment.id}
              href={`/assessments/${assessment.id}`}
              className="group block bg-card rounded-xl border border-border p-5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className="flex items-start justify-between mb-3 gap-2">
                <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                  {assessment.title || 'Untitled Assessment'}
                </h3>
                <StatusBadge status={assessment.status} />
              </div>
              <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                {assessment.description || 'No description'}
              </p>
              <div className="space-y-2 text-xs text-muted-foreground">
                <div className="flex items-center justify-between">
                  <span>Overall Impact:</span>
                  <SeverityBadge severity={assessment.overall_impact || 'Medium'} />
                </div>
                <div className="flex items-center justify-between">
                  <span>Created:</span>
                  <span className="font-medium">
                    {format(new Date(assessment.created_at), 'MMM d, yyyy')}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                {[
                  { key: 'title' as SortKey, label: 'Title' },
                  { key: 'status' as SortKey, label: 'Status' },
                  { key: 'overall_impact' as SortKey, label: 'Impact' },
                  { key: 'created_at' as SortKey, label: 'Created' },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    className="text-left px-4 py-3 font-medium text-muted-foreground cursor-pointer hover:text-foreground transition-colors select-none"
                  >
                    {col.label}
                    {sortKey === col.key && (
                      <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {paginated.map((assessment) => (
                <tr
                  key={assessment.id}
                  className="hover:bg-muted/30 transition-colors cursor-pointer"
                  onClick={() => { window.location.href = `/assessments/${assessment.id}`; }}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-foreground">{assessment.title || 'Untitled'}</div>
                    <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{assessment.description || ''}</div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={assessment.status} /></td>
                  <td className="px-4 py-3"><SeverityBadge severity={assessment.overall_impact || 'Medium'} /></td>
                  <td className="px-4 py-3 text-muted-foreground">{format(new Date(assessment.created_at), 'MMM d, yyyy')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * perPage + 1}–{Math.min(page * perPage, sorted.length)} of {sorted.length}
          </p>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
            >
              Previous
            </Button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
              .map((p, idx, arr) => (
                <span key={p} className="flex items-center">
                  {idx > 0 && arr[idx - 1] !== p - 1 && (
                    <span className="px-1 text-muted-foreground">…</span>
                  )}
                  <Button
                    variant={p === page ? 'primary' : 'ghost'}
                    size="sm"
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </Button>
                </span>
              ))}
            <Button
              variant="ghost"
              size="sm"
              disabled={page === totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
