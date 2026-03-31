'use client';

import { useEffect, useState } from 'react';
import { Search, Filter, Sparkles } from 'lucide-react';
import { SkeletonTable } from '../../components/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { StatusBadge, SeverityBadge } from '../../components/Badge';
import { Button } from '../../components/Button';
import { EmptyState } from '../../components/EmptyState';
import { Breadcrumb } from '../../components/Breadcrumb';
import ActiveRiskModal, { ActiveRiskFormData } from '../../components/ActiveRiskModal';
import { AiBadge } from '../../components/IntelligencePanel';
import apiClient from '../../lib/api-client';
import { ActiveRisk } from '../../lib/types';
import { format } from 'date-fns';

export default function ActiveRisksPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [risks, setRisks] = useState<ActiveRisk[]>([]);
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [editingRisk, setEditingRisk] = useState<ActiveRisk | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    loadRisks();
  }, [statusFilter]);

  const loadRisks = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (statusFilter !== 'all') {
        params.status = statusFilter;
      }
      const items = await apiClient.getActiveRisks(params);
      setRisks(items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load active risks');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptRisk = async (riskId: string) => {
    if (!confirm('Are you sure you want to accept this risk?')) {
      return;
    }

    try {
      await apiClient.acceptRisk(riskId);
      loadRisks();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to accept risk');
    }
  };

  const handleEditRisk = async (formData: ActiveRiskFormData) => {
    if (!editingRisk) return;

    try {
      await apiClient.updateActiveRisk(editingRisk.id, formData);
      loadRisks();
      setIsModalOpen(false);
      setEditingRisk(null);
    } catch (err: any) {
      throw err;
    }
  };

  const openEditModal = (risk: ActiveRisk) => {
    setEditingRisk(risk);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRisk(null);
  };

  const filteredRisks = risks.filter((risk) =>
    risk.title.toLowerCase().includes(filter.toLowerCase())
  );

  const risksByStatus = {
    open: filteredRisks.filter((r) => r.status === 'open').length,
    accepted: filteredRisks.filter((r) => r.status === 'accepted').length,
    mitigating: filteredRisks.filter((r) => r.status === 'mitigating').length,
    closed: filteredRisks.filter((r) => r.status === 'closed').length,
  };

  const risksBySeverity = {
    Critical: filteredRisks.filter((r) => r.residual_risk === 'Critical').length,
    High: filteredRisks.filter((r) => r.residual_risk === 'High').length,
    Medium: filteredRisks.filter((r) => r.residual_risk === 'Medium').length,
    Low: filteredRisks.filter((r) => r.residual_risk === 'Low').length,
  };

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
      <Breadcrumb items={[{ label: 'Risk Register' }]} />

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Risk Register</h1>
        <p className="text-muted-foreground mt-1">Active risks requiring attention and management</p>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card rounded-xl border border-border p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">By Status</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(risksByStatus).map(([status, count]) => (
              <div key={status} className="text-center">
                <p className="text-2xl font-bold text-foreground">{count}</p>
                <p className="text-xs text-muted-foreground mt-1 capitalize">{status}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card rounded-xl border border-border p-5">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">By Severity</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(risksBySeverity).map(([severity, count]) => (
              <div key={severity} className="text-center">
                <p className="text-2xl font-bold text-foreground">{count}</p>
                <p className="text-xs text-muted-foreground mt-1">{severity}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search risks..."
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
            <option value="open">Open</option>
            <option value="accepted">Accepted</option>
            <option value="mitigating">Mitigating</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      {/* Risks Table */}
      {filteredRisks.length === 0 ? (
        <div className="bg-card rounded-xl border border-border">
          <EmptyState
            icon={filter ? 'search' : 'risks'}
            title={filter ? 'No matching risks' : 'No active risks'}
            description={filter ? 'Try adjusting your search or filters' : 'Risks will appear here when threats are sent to the risk register'}
          />
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden shadow-sm">
          <table className="min-w-full divide-y divide-border">
            <thead>
              <tr className="bg-muted/50">
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Risk Statement
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Risk Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Review Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredRisks.map((risk) => (
                <tr 
                  key={risk.id} 
                  className="hover:bg-muted/30 cursor-pointer transition-colors"
                  onClick={() => openEditModal(risk)}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground max-w-md">
                        {risk.title}
                      </span>
                      {risk.detected_by === 'ai_intelligence' && <AiBadge />}
                    </div>
                    {risk.mitigation_plan && (
                      <div className="text-xs text-muted-foreground mt-1">
                        {risk.mitigation_plan}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <SeverityBadge severity={risk.residual_risk} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      risk.risk_status === 'Completed' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400' :
                      risk.risk_status === 'Ongoing' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                      risk.risk_status === 'Delayed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                      risk.risk_status === 'Accepted' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400' :
                      'bg-muted text-muted-foreground'
                    }`}>
                      {risk.risk_status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                    {risk.review_cycle_days ? `Every ${risk.review_cycle_days} days` : 'Not set'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                    {risk.status === 'open' && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleAcceptRisk(risk.id)}
                      >
                        Accept Risk
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editingRisk && (
        <ActiveRiskModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSubmit={handleEditRisk}
          risk={editingRisk}
        />
      )}
    </div>
  );
}
