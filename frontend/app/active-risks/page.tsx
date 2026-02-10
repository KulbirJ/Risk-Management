'use client';

import { useEffect, useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { LoadingPage } from '../../components/LoadingSpinner';
import { Alert } from '../../components/Alert';
import { StatusBadge, SeverityBadge } from '../../components/Badge';
import { Button } from '../../components/Button';
import ActiveRiskModal, { ActiveRiskFormData } from '../../components/ActiveRiskModal';
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
    return <LoadingPage />;
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Risk Register</h1>
        <p className="text-gray-600 mt-1">Active risks requiring attention and management</p>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-4">By Status</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(risksByStatus).map(([status, count]) => (
              <div key={status} className="text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-xs text-gray-500 mt-1 capitalize">{status}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-4">By Severity</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(risksBySeverity).map(([severity, count]) => (
              <div key={severity} className="text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-xs text-gray-500 mt-1">{severity}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search risks..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
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
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No active risks found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Statement
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Severity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Review Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredRisks.map((risk) => (
                <tr 
                  key={risk.id} 
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => openEditModal(risk)}
                >
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 max-w-md">
                      {risk.title}
                    </div>
                    {risk.mitigation_plan && (
                      <div className="text-xs text-gray-500 mt-1">
                        {risk.mitigation_plan}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <SeverityBadge severity={risk.residual_risk} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      risk.risk_status === 'Completed' ? 'bg-green-100 text-green-800' :
                      risk.risk_status === 'Ongoing' ? 'bg-blue-100 text-blue-800' :
                      risk.risk_status === 'Delayed' ? 'bg-red-100 text-red-800' :
                      risk.risk_status === 'Accepted' ? 'bg-purple-100 text-purple-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {risk.risk_status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
