'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Edit, Trash2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/Button';
import { LoadingPage } from '@/components/LoadingSpinner';
import { Alert } from '@/components/Alert';
import { StatusBadge, SeverityBadge } from '@/components/Badge';
import { ThreatModal, ThreatFormData } from '@/components/ThreatModal';
import apiClient from '@/lib/api-client';
import { Assessment, Threat, ActiveRisk } from '@/lib/types';
import { format } from 'date-fns';

export default function AssessmentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const assessmentId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [threats, setThreats] = useState<Threat[]>([]);
  const [isThreatModalOpen, setIsThreatModalOpen] = useState(false);
  const [editingThreat, setEditingThreat] = useState<Threat | null>(null);

  useEffect(() => {
    loadAssessmentData();
  }, [assessmentId]);

  const loadAssessmentData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [assessmentData, threatsData] = await Promise.all([
        apiClient.getAssessment(assessmentId),
        apiClient.getThreats(assessmentId),
      ]);

      setAssessment(assessmentData);
      setThreats(threatsData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load assessment');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAssessment = async () => {
    if (!confirm('Are you sure you want to delete this assessment? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.deleteAssessment(assessmentId);
      router.push('/assessments');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete assessment');
    }
  };

  const handleAddThreat = async (formData: ThreatFormData) => {
    try {
      const payload = {
        title: formData.title,
        description: formData.description || '',
        recommendation: formData.recommendation || '',
        likelihood: formData.likelihood,
        impact: formData.impact,
        cve_ids: formData.cve_ids || [],
      };

      await apiClient.createThreat(assessmentId, payload);
      await loadAssessmentData(); // Reload to show new threat
      setIsThreatModalOpen(false);
      setEditingThreat(null);
    } catch (err: any) {
      console.error('Failed to add threat:', err);
      throw err; // Re-throw so modal can handle it
    }
  };

  const handleEditThreat = async (formData: ThreatFormData) => {
    if (!editingThreat) return;

    try {
      const payload: any = {
        title: formData.title,
        description: formData.description || '',
        recommendation: formData.recommendation || '',
        likelihood: formData.likelihood,
        impact: formData.impact,
      };

      console.log('Updating threat with payload:', payload);

      // Add status if it changed
      if (formData.status && formData.status !== editingThreat.status) {
        payload.status = formData.status;

        // If status changed to 'at_risk', create an active risk entry
        if (formData.status === 'at_risk' && editingThreat.status !== 'at_risk') {
          // Create risk register entry
          const activeRiskPayload: Partial<ActiveRisk> = {
            threat_id: editingThreat.id,
            title: formData.title,
            residual_risk: formData.impact as 'Low' | 'Medium' | 'High' | 'Critical',
            risk_owner_id: assessment?.owner_user_id || '',
            mitigation_plan: formData.description || '',
            review_cycle_days: 30,
            risk_status: 'Planned',
          };

          await apiClient.createActiveRisk(assessmentId, activeRiskPayload);
        }
      }

      await apiClient.updateThreat(editingThreat.id, payload);
      await loadAssessmentData(); // Reload to show updated threat
      setIsThreatModalOpen(false);
      setEditingThreat(null);
    } catch (err: any) {
      console.error('Failed to update threat:', err);
      throw err; // Re-throw so modal can handle it
    }
  };

  const handleDeleteThreat = async (threatId: string) => {
    if (!confirm('Are you sure you want to delete this threat? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.deleteThreat(threatId);
      await loadAssessmentData(); // Reload to show remaining threats
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete threat');
    }
  };

  const openEditThreatModal = (threat: Threat) => {
    setEditingThreat(threat);
    setIsThreatModalOpen(true);
  };

  const closeModal = () => {
    setIsThreatModalOpen(false);
    setEditingThreat(null);
  };

  if (loading) {
    return <LoadingPage />;
  }

  if (!assessment) {
    return (
      <div className="text-center py-12">
        <Alert type="error" message="Assessment not found" />
        <Link href="/assessments" className="text-primary hover:underline mt-4 inline-block">
          Back to Assessments
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link href="/assessments" className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Assessments
      </Link>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* Assessment Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{assessment.title}</h1>
              <StatusBadge status={assessment.status} />
            </div>
            <p className="text-gray-600">{assessment.description || 'No description'}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm">
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </Button>
            <Button variant="danger" size="sm" onClick={handleDeleteAssessment}>
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 text-sm">
          <div>
            <span className="text-gray-500">Overall Impact:</span>
            <p className="font-medium capitalize mt-1">{assessment.overall_impact}</p>
          </div>
          <div>
            <span className="text-gray-500">Created:</span>
            <p className="font-medium mt-1">
              {format(new Date(assessment.created_at), 'MMM d, yyyy')}
            </p>
          </div>
          <div>
            <span className="text-gray-500">Last Updated:</span>
            <p className="font-medium mt-1">
              {format(new Date(assessment.updated_at), 'MMM d, yyyy')}
            </p>
          </div>
        </div>
      </div>

      {/* Threats List */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Identified Threats</h2>
        <Button size="sm" onClick={() => setIsThreatModalOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Threat
        </Button>
      </div>

      {threats.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600 mb-4">No threats identified yet</p>
          <Button size="sm" onClick={() => setIsThreatModalOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add First Threat
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {threats.map((threat) => (
            <div
              key={threat.id}
              className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md hover:border-primary transition-all cursor-pointer relative group"
              onClick={() => openEditThreatModal(threat)}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">{threat.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{threat.description}</p>
                  {threat.recommendation && (
                    <div className="mt-2 p-2 bg-blue-50 border-l-2 border-blue-500 rounded">
                      <span className="text-xs font-medium text-blue-700">Recommendation:</span>
                      <p className="text-sm text-blue-900 mt-1">{threat.recommendation}</p>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={threat.severity} />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteThreat(threat.id);
                    }}
                    className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete threat"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Status:</span>
                  <p className="font-medium mt-1 capitalize">{threat.status.replace('_', ' ')}</p>
                </div>
                <div>
                  <span className="text-gray-500">Likelihood:</span>
                  <p className="font-medium mt-1">{threat.likelihood}</p>
                </div>
                <div>
                  <span className="text-gray-500">Impact:</span>
                  <p className="font-medium mt-1">{threat.impact}</p>
                </div>
                <div>
                  <span className="text-gray-500">CVE IDs:</span>
                  <p className="font-medium mt-1">{threat.cve_ids?.length || 0}</p>
                </div>
              </div>
              <div className="absolute top-4 right-16 text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
                Click to edit
              </div>
            </div>
          ))}
        </div>
      )}

      <ThreatModal
        isOpen={isThreatModalOpen}
        onClose={closeModal}
        onSubmit={editingThreat ? handleEditThreat : handleAddThreat}
        assessmentId={assessmentId}
        threat={editingThreat}
      />
    </div>
  );
}
