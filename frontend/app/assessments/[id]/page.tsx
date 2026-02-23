'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Edit, Trash2, AlertTriangle, Lightbulb, Shield, Upload, FileText, Download, X, Check, Loader2, RefreshCw, Sparkles, UserCheck, ChevronDown, ArrowRightCircle, Brain, Network, Boxes, Database } from 'lucide-react';
import { Button } from '../../../components/Button';
import { LoadingPage } from '../../../components/LoadingSpinner';
import { Alert } from '../../../components/Alert';
import { StatusBadge, SeverityBadge } from '../../../components/Badge';
import { ThreatModal, ThreatFormData } from '../../../components/ThreatModal';
import { IntelligencePanel, AiBadge } from '../../../components/IntelligencePanel';
import { AttackContextPanel } from '../../../components/AttackContextPanel';
import { IntelEnrichmentPanel, EnrichmentBadge } from '../../../components/IntelEnrichmentPanel';
import { MLScoringPanel, MLScoreBadge } from '../../../components/MLScoringPanel';
import { ThreatGraphPanel } from '../../../components/ThreatGraphPanel';
import { ClusteringPanel } from '../../../components/ClusteringPanel';
import apiClient from '../../../lib/api-client';
import { Assessment, Threat, ActiveRisk, Recommendation, Evidence } from '../../../lib/types';
import { format } from 'date-fns';

export default function AssessmentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const assessmentId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [threats, setThreats] = useState<Threat[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [activeRisks, setActiveRisks] = useState<ActiveRisk[]>([]);
  const [isThreatModalOpen, setIsThreatModalOpen] = useState(false);
  const [editingThreat, setEditingThreat] = useState<Threat | null>(null);
  const [isEditingAssessment, setIsEditingAssessment] = useState(false);
  const INDUSTRY_SECTORS = [
    { value: '', label: 'Select industry sector (optional)' },
    { value: 'technology', label: 'Technology & Software' },
    { value: 'finance', label: 'Finance & Banking' },
    { value: 'healthcare', label: 'Healthcare & Life Sciences' },
    { value: 'government', label: 'Government & Public Sector' },
    { value: 'energy', label: 'Energy & Utilities' },
    { value: 'manufacturing', label: 'Manufacturing & Industrial' },
    { value: 'retail', label: 'Retail & E-Commerce' },
    { value: 'education', label: 'Education' },
    { value: 'media', label: 'Media & Telecommunications' },
    { value: 'transportation', label: 'Transportation & Logistics' },
    { value: 'legal', label: 'Legal & Professional Services' },
    { value: 'other', label: 'Other' },
  ];

  const [editFormData, setEditFormData] = useState({
    title: '',
    description: '',
    system_background: '',
    scope: '',
    industry_sector: '',
    overall_impact: 'Medium',
    status: 'draft',
  });
  const [editSaving, setEditSaving] = useState(false);

  // Evidence / Upload state
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [threatsExpanded, setThreatsExpanded] = useState(false);

  // Analytics tab state
  const [analyticsTab, setAnalyticsTab] = useState<'intel' | 'ml' | 'graph' | 'cluster'>('intel');

  const ALLOWED_TYPES = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/csv',
    'application/json',
    'application/xml',
    'text/xml',
    'text/plain',
    'image/png',
    'image/jpeg',
  ];
  const MAX_SIZE_MB = 10;

  useEffect(() => {
    loadAssessmentData();
  }, [assessmentId]);

  const loadAssessmentData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [assessmentData, threatsData, recommendationsData, activeRisksData, evidenceData] = await Promise.all([
        apiClient.getAssessment(assessmentId),
        apiClient.getThreats(assessmentId),
        apiClient.getRecommendations({ assessment_id: assessmentId }).catch(() => []),
        apiClient.getActiveRisks({ assessment_id: assessmentId }).catch(() => []),
        apiClient.getEvidence({ assessment_id: assessmentId }).catch(() => []),
      ]);

      setAssessment(assessmentData);
      setThreats(threatsData);
      setRecommendations(recommendationsData);
      setActiveRisks(activeRisksData);
      setEvidenceList(evidenceData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load assessment');
    } finally {
      setLoading(false);
    }
  };

  const handleEditAssessment = () => {
    if (!assessment) return;
    setEditFormData({
      title: assessment.title || '',
      description: assessment.description || '',
      system_background: assessment.system_background || '',
      scope: assessment.scope || '',
      industry_sector: assessment.industry_sector || '',
      overall_impact: assessment.overall_impact || 'Medium',
      status: assessment.status || 'draft',
    });
    setIsEditingAssessment(true);
  };

  const handleSaveAssessment = async () => {
    try {
      setEditSaving(true);
      setError(null);
      await apiClient.updateAssessment(assessmentId, editFormData as Partial<Assessment>);
      await loadAssessmentData();
      setIsEditingAssessment(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update assessment');
    } finally {
      setEditSaving(false);
    }
  };

  const handleDeleteAssessment = async () => {
    if (!confirm('Are you sure you want to delete this assessment? This action cannot be undone.')) {
      return;
    }

    try {
      await apiClient.deleteAssessment(assessmentId);
      router.replace('/assessments');
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
          const ownerId = assessment?.owner_user_id || '0bc9d6a9-f342-452e-9297-ee33f44d4f84';
          const activeRiskPayload = {
            threat_id: editingThreat.id,
            title: formData.title,
            residual_risk: formData.impact as 'Low' | 'Medium' | 'High' | 'Critical',
            risk_owner_id: ownerId,
            mitigation_plan: formData.description || 'Mitigation plan pending',
            review_cycle_days: 30,
            risk_status: 'Planned',
          };

          try {
            await apiClient.createActiveRisk(assessmentId, activeRiskPayload as Partial<ActiveRisk>);
          } catch (riskErr: any) {
            console.warn('Failed to create active risk entry:', riskErr);
            // Continue with threat update even if risk creation fails
          }
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

  const handlePromoteThreat = async (threatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.promoteThreat(threatId);
      await loadAssessmentData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to promote threat');
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

  // === Evidence Upload Handlers ===
  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setUploadError(null);
    setIsUploading(true);

    try {
      for (const file of Array.from(files)) {
        // Validate file size
        if (file.size > MAX_SIZE_MB * 1024 * 1024) {
          setUploadError(`File "${file.name}" exceeds ${MAX_SIZE_MB}MB limit`);
          continue;
        }

        // Step 1: Get presigned URL from backend
        const initResponse = await apiClient.initiateUpload(assessmentId, file);

        try {
          // Step 2: Upload directly to S3
          await apiClient.uploadToS3(initResponse.upload_url, initResponse.upload_fields, file);

          // Step 3: Tell backend upload is complete → triggers parsing
          await apiClient.completeUpload(initResponse.evidence_id);
        } catch (uploadErr) {
          // Clean up the orphaned evidence record so it doesn't stay as "processing"
          try { await apiClient.deleteEvidence(initResponse.evidence_id); } catch (_) {}
          throw uploadErr;
        }
      }

      // Reload evidence list
      await loadAssessmentData();
    } catch (err: any) {
      console.error('Upload failed:', err);
      setUploadError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const handleDeleteEvidence = async (evidenceId: string) => {
    if (!confirm('Delete this file?')) return;
    try {
      await apiClient.deleteEvidence(evidenceId);
      await loadAssessmentData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete file');
    }
  };

  const handleDownloadEvidence = async (evidenceId: string) => {
    try {
      const { download_url, file_name } = await apiClient.getDownloadUrl(evidenceId);
      const link = document.createElement('a');
      link.href = download_url;
      link.download = file_name;
      link.click();
    } catch (err: any) {
      setError('Failed to get download link');
    }
  };

  const handleRetryEvidence = async (evidenceId: string) => {
    try {
      await apiClient.retryEvidence(evidenceId);
      await loadAssessmentData();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Retry failed. You may need to delete and re-upload.';
      setUploadError(msg);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getDocTypeLabel = (type?: string) => {
    const labels: Record<string, string> = {
      vulnerability_scan: 'Vuln Scan',
      architecture_doc: 'Architecture',
      policy: 'Policy',
      config: 'Config',
      other: 'Document',
    };
    return labels[type || 'other'] || type || 'Document';
  };

  const getStatusIcon = (status: string) => {
    if (status === 'processing') return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
    if (status === 'ready') return <Check className="w-4 h-4 text-green-500" />;
    return <X className="w-4 h-4 text-red-500" />;
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
            <Button variant="ghost" size="sm" onClick={handleEditAssessment}>
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </Button>
            <Button variant="danger" size="sm" onClick={handleDeleteAssessment}>
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        {isEditingAssessment ? (
          <div className="mt-4 space-y-4 border-t border-gray-200 pt-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={editFormData.title}
                onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={editFormData.description}
                onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">System Background</label>
                <textarea
                  value={editFormData.system_background}
                  onChange={(e) => setEditFormData({ ...editFormData, system_background: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Scope</label>
                <textarea
                  value={editFormData.scope}
                  onChange={(e) => setEditFormData({ ...editFormData, scope: e.target.value })}
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Industry Sector</label>
                <select
                  value={editFormData.industry_sector}
                  onChange={(e) => setEditFormData({ ...editFormData, industry_sector: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {INDUSTRY_SECTORS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Overall Impact</label>
                <select
                  value={editFormData.overall_impact}
                  onChange={(e) => setEditFormData({ ...editFormData, overall_impact: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={editFormData.status}
                  onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="draft">Draft</option>
                  <option value="in_review">In Review</option>
                  <option value="completed">Completed</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={() => setIsEditingAssessment(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleSaveAssessment} disabled={editSaving}>
                {editSaving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-6 text-sm">
            <div>
              <span className="text-gray-500">Overall Impact:</span>
              <p className="font-medium capitalize mt-1">{assessment.overall_impact}</p>
            </div>
            <div>
              <span className="text-gray-500">Industry Sector:</span>
              <p className="font-medium capitalize mt-1">
                {assessment.industry_sector
                  ? assessment.industry_sector.replace(/_/g, ' ')
                  : <span className="text-gray-400 italic">Not set</span>}
              </p>
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
        )}
      </div>

      {/* AI Intelligence Panel */}
      <IntelligencePanel
        assessmentId={assessmentId}
        onEnrichComplete={loadAssessmentData}
      />

      {/* Evidence & Documents Upload Section */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-500" />
          Evidence & Documents ({evidenceList.length})
        </h2>

        {/* Drop Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors mb-4 ${
            dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white'
          }`}
        >
          <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600 mb-2">
            Drag & drop files here, or{' '}
            <label className="text-blue-600 hover:underline cursor-pointer">
              browse
              <input
                type="file"
                multiple
                className="hidden"
                accept=".pdf,.docx,.xlsx,.xls,.csv,.json,.xml,.txt,.md,.log,.png,.jpg,.jpeg"
                onChange={(e) => handleFileUpload(e.target.files)}
                disabled={isUploading}
              />
            </label>
          </p>
          <p className="text-xs text-gray-400">
            PDF, DOCX, XLSX, CSV, JSON, XML, TXT, images — max {MAX_SIZE_MB}MB per file
          </p>
          {isUploading && (
            <div className="flex items-center justify-center gap-2 mt-3 text-blue-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Uploading & processing...</span>
            </div>
          )}
          {uploadError && (
            <p className="text-sm text-red-600 mt-2">{uploadError}</p>
          )}
        </div>

        {/* Evidence List */}
        {evidenceList.length > 0 && (
          <div className="space-y-2">
            {evidenceList.map((ev) => (
              <div
                key={ev.id}
                className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  {getStatusIcon(ev.status)}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{ev.file_name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded font-medium">
                        {getDocTypeLabel(ev.document_type)}
                      </span>
                      <span>{formatFileSize(ev.size_bytes)}</span>
                      <span>{format(new Date(ev.created_at), 'MMM d, yyyy')}</span>
                      {ev.status === 'ready' && ev.extracted_text && (
                        <span className="text-green-600">
                          {ev.extracted_text.length.toLocaleString()} chars extracted
                        </span>
                      )}
                      {ev.status === 'failed' && (
                        <span className="text-red-600">Processing failed</span>
                      )}
                      {ev.status === 'processing' && (
                        <span className="text-blue-600">Processing...</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  {(ev.status === 'processing' || ev.status === 'failed') && (
                    <button
                      onClick={() => handleRetryEvidence(ev.id)}
                      className="p-2 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded-md transition-colors"
                      title="Retry processing"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}
                  {ev.status === 'ready' && (
                    <button
                      onClick={() => handleDownloadEvidence(ev.id)}
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteEvidence(ev.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {evidenceList.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-2">
            Upload vulnerability scans, architecture docs, or other evidence to improve AI threat analysis.
          </p>
        )}
      </div>

      {/* Advanced Analytics Section */}
      <div className="bg-white rounded-lg border border-gray-200 mb-6">
        <div className="border-b border-gray-200 px-4">
          <nav className="flex -mb-px gap-1">
            {[
              { key: 'intel' as const, label: 'Intel Enrichment', icon: Database },
              { key: 'ml' as const, label: 'ML Scoring', icon: Brain },
              { key: 'graph' as const, label: 'Threat Graph', icon: Network },
              { key: 'cluster' as const, label: 'Clustering', icon: Boxes },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setAnalyticsTab(tab.key)}
                className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  analyticsTab === tab.key
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="p-4">
          {analyticsTab === 'intel' && (
            <IntelEnrichmentPanel assessmentId={assessmentId} threatIds={threats.map(t => t.id)} onEnrichComplete={loadAssessmentData} />
          )}
          {analyticsTab === 'ml' && (
            <MLScoringPanel assessmentId={assessmentId} onScoreComplete={loadAssessmentData} />
          )}
          {analyticsTab === 'graph' && (
            <ThreatGraphPanel assessmentId={assessmentId} />
          )}
          {analyticsTab === 'cluster' && (
            <ClusteringPanel assessmentId={assessmentId} />
          )}
        </div>
      </div>

      {/* Threats List */}
      <div className="mb-6">
        <button
          onClick={() => setThreatsExpanded(!threatsExpanded)}
          className="w-full flex items-center justify-between py-3 px-1 group"
        >
          <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Identified Threats ({threats.length})
          </h2>
          <div className="flex items-center gap-2">
            <div onClick={(e) => e.stopPropagation()}>
              <Button size="sm" onClick={() => { setIsThreatModalOpen(true); }}>
                <Plus className="w-4 h-4 mr-2" />
                Add Threat
              </Button>
            </div>
            <ChevronDown className={`w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-transform duration-200 ${threatsExpanded ? 'rotate-0' : '-rotate-90'}`} />
          </div>
        </button>
      </div>

      {threatsExpanded && (threats.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600 mb-4">No threats identified yet</p>
          <Button size="sm" onClick={() => setIsThreatModalOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add First Threat
          </Button>
        </div>
      ) : (
        <>
          {/* Analyst Assessed Section */}
          {(() => {
            const analystThreats = threats.filter(t => t.detected_by !== 'ai_intelligence');
            if (analystThreats.length === 0) return null;
            return (
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-1.5 bg-emerald-100 rounded-md">
                    <Check className="w-4 h-4 text-emerald-600" />
                  </div>
                  <h3 className="text-base font-semibold text-gray-800">
                    Analyst Assessed
                  </h3>
                  <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-medium">{analystThreats.length}</span>
                  <span className="text-xs text-gray-500 ml-1">Protected from AI re-runs</span>
                </div>
                <div className="space-y-4">
                  {analystThreats.map((threat) => (
                    <ThreatCard key={threat.id} threat={threat} onEdit={openEditThreatModal} onDelete={handleDeleteThreat} recommendations={recommendations.filter(r => r.threat_id === threat.id)} />
                  ))}
                </div>
              </div>
            );
          })()}

          {/* AI Assessed Section */}
          {(() => {
            const aiThreats = threats.filter(t => t.detected_by === 'ai_intelligence');
            if (aiThreats.length === 0) return null;
            return (
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-1.5 bg-indigo-100 rounded-md">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                  </div>
                  <h3 className="text-base font-semibold text-gray-800">
                    AI Assessed
                  </h3>
                  <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">{aiThreats.length}</span>
                  <span className="text-xs text-gray-500 ml-1">Will be refreshed on next AI enrichment</span>
                </div>
                <div className="space-y-4">
                  {aiThreats.map((threat) => (
                    <ThreatCard
                      key={threat.id}
                      threat={threat}
                      onEdit={openEditThreatModal}
                      onDelete={handleDeleteThreat}
                      onPromote={handlePromoteThreat}
                      showPromote
                      recommendations={recommendations.filter(r => r.threat_id === threat.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })()}
        </>
      ))}

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

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-green-100 text-green-700',
    High: 'bg-red-100 text-red-700',
    Medium: 'bg-yellow-100 text-yellow-700',
    Low: 'bg-green-100 text-green-700',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[priority] || 'bg-gray-100 text-gray-700'}`}>
      {priority}
    </span>
  );
}

function ThreatCard({
  threat,
  onEdit,
  onDelete,
  onPromote,
  showPromote = false,
  recommendations = [],
}: {
  threat: Threat;
  onEdit: (threat: Threat) => void;
  onDelete: (id: string) => void;
  onPromote?: (id: string, e: React.MouseEvent) => void;
  showPromote?: boolean;
  recommendations?: Recommendation[];
}) {
  return (
    <div
      className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-lg transition-all cursor-pointer relative group"
      onClick={() => onEdit(threat)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-semibold text-gray-900 leading-tight">
              {threat.title}
            </h3>
            {threat.detected_by === 'ai_intelligence' && <AiBadge />}
            {threat.detected_by === 'analyst_assessed' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200">
                <UserCheck className="w-3 h-3" />
                Analyst Reviewed
              </span>
            )}
            <EnrichmentBadge threatId={threat.id} />
            <MLScoreBadge threatId={threat.id} />
            <SeverityBadge severity={threat.severity} />
          </div>
          {threat.description && (
            <p className="text-sm text-gray-600 mt-1.5 line-clamp-2">{threat.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(threat); }}
            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            title="Edit threat"
          >
            <Edit className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(threat.id); }}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete threat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Metadata row */}
      <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
        <span className="capitalize">Status: <strong className="text-gray-700">{threat.status.replace('_', ' ')}</strong></span>
        <span>Likelihood: <strong className="text-gray-700">{threat.likelihood}</strong></span>
        <span>Impact: <strong className="text-gray-700">{threat.impact}</strong></span>
        {threat.cve_ids?.length > 0 && <span>CVEs: <strong className="text-gray-700">{threat.cve_ids.length}</strong></span>}
      </div>

      {/* AI Rationale */}
      {threat.ai_rationale && (
        <div className="mt-3 p-2.5 bg-indigo-50/70 border border-indigo-100 rounded-lg">
          <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">AI Rationale</span>
          <p className="text-sm text-indigo-900 mt-0.5">{threat.ai_rationale}</p>
        </div>
      )}

      {/* Inline Recommendation (from threat field) */}
      {threat.recommendation && (
        <div className="mt-3 p-2.5 bg-amber-50/70 border border-amber-100 rounded-lg">
          <div className="flex items-center gap-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-amber-600" />
            <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Recommendation</span>
          </div>
          <p className="text-sm text-amber-900 mt-0.5">{threat.recommendation}</p>
        </div>
      )}

      {/* Linked Recommendations from separate records */}
      {recommendations.length > 0 && (
        <div className="mt-3 space-y-2">
          {recommendations.map((rec) => (
            <div key={rec.id} className="p-2.5 bg-green-50/70 border border-green-100 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Lightbulb className="w-3.5 h-3.5 text-green-600" />
                  <span className="text-xs font-semibold text-green-700">{rec.title || 'Recommendation'}</span>
                  {rec.ai_generated && <AiBadge />}
                  <PriorityBadge priority={rec.priority} />
                </div>
                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                  rec.status === 'implemented' ? 'bg-green-100 text-green-700' :
                  rec.status === 'approved' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>{rec.status}</span>
              </div>
              <p className="text-sm text-green-900 mt-1">{rec.description || rec.text || ''}</p>
              {(rec.estimated_effort || rec.cost_estimate) && (
                <div className="flex gap-3 mt-1 text-xs text-green-600">
                  {rec.estimated_effort && <span>Effort: {rec.estimated_effort}</span>}
                  {rec.cost_estimate && <span>Cost: {rec.cost_estimate}</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Send to Analyst button */}
      {showPromote && onPromote && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <button
            onClick={(e) => onPromote(threat.id, e)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-emerald-500 hover:from-indigo-600 hover:to-emerald-600 rounded-lg shadow-sm hover:shadow-md transition-all"
          >
            <ArrowRightCircle className="w-4 h-4" />
            Send to Analyst
          </button>
        </div>
      )}

      {/* ATT&CK Context */}
      <AttackContextPanel threatId={threat.id} threatTitle={threat.title} />
    </div>
  );
}
