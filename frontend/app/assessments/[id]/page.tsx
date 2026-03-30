'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Plus, Edit, Trash2, AlertTriangle, Lightbulb, Shield, Upload, FileText, Download, X, Check, Loader2, Sparkles, UserCheck, ChevronDown, ChevronRight, ArrowRightCircle, Brain, Network, Boxes, Database, MoreHorizontal, Wrench } from 'lucide-react';
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
import { TriggerAssessmentButton } from '../../../components/TriggerAssessmentButton';
import { EvidenceDetailModal } from '../../../components/EvidenceDetailModal';
import { CompliancePanel } from '../../../components/CompliancePanel';
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
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [threatsExpanded, setThreatsExpanded] = useState(true); // default expanded per UX plan

  // Analytics tab state
  const [analyticsTab, setAnalyticsTab] = useState<'evidence' | 'enrichment' | 'ml' | 'graph' | 'cluster' | 'compliance'>('evidence');

  // Tools & Analysis section collapsed by default
  const [toolsExpanded, setToolsExpanded] = useState(false);

  // Overflow menu state
  const [showOverflow, setShowOverflow] = useState(false);
  const overflowRef = useRef<HTMLDivElement>(null);

  // Threat view tab: analyst vs ai
  const [threatViewTab, setThreatViewTab] = useState<'all' | 'analyst' | 'ai'>('all');

  // Expanded threat card IDs (progressive disclosure)
  const [expandedThreats, setExpandedThreats] = useState<Set<string>>(new Set());

  // Metadata expanded
  const [metadataExpanded, setMetadataExpanded] = useState(false);

  // Close overflow menu on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (overflowRef.current && !overflowRef.current.contains(e.target as Node)) {
        setShowOverflow(false);
      }
    };
    if (showOverflow) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showOverflow]);

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
  const MAX_SIZE_MB = 20;

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
          // Step 2: Upload file directly to S3 via presigned POST
          await apiClient.uploadToS3(
            initResponse.upload_url,
            initResponse.upload_fields,
            file,
            initResponse.upload_method ?? 'POST',
          );

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
      network_diagram: 'Network Diagram',
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

  // Severity distribution helpers
  const severityCounts = threats.reduce((acc, t) => {
    const sev = (t.severity || 'Medium') as string;
    acc[sev] = (acc[sev] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const analystThreats = threats.filter(t => t.detected_by !== 'ai_intelligence');
  const aiThreats = threats.filter(t => t.detected_by === 'ai_intelligence');
  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  const sortBySeverity = (list: Threat[]) =>
    [...list].sort((a, b) => (severityOrder[a.severity?.toLowerCase()] ?? 4) - (severityOrder[b.severity?.toLowerCase()] ?? 4));
  const filteredThreats = sortBySeverity(threatViewTab === 'analyst' ? analystThreats : threatViewTab === 'ai' ? aiThreats : threats);

  const toggleThreatExpand = (id: string) => {
    setExpandedThreats(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // Tools summary line
  const toolsSummary = [
    evidenceList.length > 0 ? `${evidenceList.length} evidence file${evidenceList.length !== 1 ? 's' : ''}` : null,
    threats.length > 0 ? 'ML scored' : null,
  ].filter(Boolean).join(' · ') || 'No data yet';

  return (
    <div>
      <Link href="/assessments" className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Assessments
      </Link>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      {/* ═══════════════════════════════════════════════════════════
          ZONE A — Context Bar (compact header)
         ═══════════════════════════════════════════════════════════ */}
      <div className="bg-white rounded-lg border border-gray-200 p-5 mb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900 truncate">{assessment.title}</h1>
              <StatusBadge status={assessment.status} />
              <SeverityBadge severity={assessment.overall_impact || 'Medium'} />
            </div>
            {assessment.description && (
              <p className="text-sm text-gray-600 line-clamp-1">{assessment.description}</p>
            )}
          </div>

          {/* Action buttons: Primary + Overflow */}
          <div className="flex items-center gap-2 shrink-0">
            <TriggerAssessmentButton
              assessmentId={assessmentId}
              onComplete={loadAssessmentData}
            />
            <div className="relative" ref={overflowRef}>
              <button
                onClick={() => setShowOverflow(!showOverflow)}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="More actions"
              >
                <MoreHorizontal className="w-5 h-5" />
              </button>
              {showOverflow && (
                <div className="absolute right-0 top-full mt-1 w-44 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-20">
                  <Link
                    href={`/assessments/${assessmentId}/report`}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    onClick={() => setShowOverflow(false)}
                  >
                    <FileText className="w-4 h-4" />
                    View Report
                  </Link>
                  <button
                    onClick={() => { setShowOverflow(false); handleEditAssessment(); }}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left"
                  >
                    <Edit className="w-4 h-4" />
                    Edit Assessment
                  </button>
                  <hr className="my-1 border-gray-100" />
                  <button
                    onClick={() => { setShowOverflow(false); handleDeleteAssessment(); }}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Expandable metadata row */}
        <button
          onClick={() => setMetadataExpanded(!metadataExpanded)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 mt-2 transition-colors"
        >
          <ChevronRight className={`w-3 h-3 transition-transform ${metadataExpanded ? 'rotate-90' : ''}`} />
          {assessment.industry_sector
            ? assessment.industry_sector.replace(/_/g, ' ')
            : 'Details'}
          {' · '}
          {format(new Date(assessment.created_at), 'MMM d, yyyy')}
        </button>

        {metadataExpanded && !isEditingAssessment && (
          <div className="grid grid-cols-4 gap-6 text-sm mt-3 pt-3 border-t border-gray-100">
            <div>
              <span className="text-gray-500">Overall Impact:</span>
              <p className="font-medium capitalize mt-0.5">{assessment.overall_impact}</p>
            </div>
            <div>
              <span className="text-gray-500">Industry Sector:</span>
              <p className="font-medium capitalize mt-0.5">
                {assessment.industry_sector
                  ? assessment.industry_sector.replace(/_/g, ' ')
                  : <span className="text-gray-400 italic">Not set</span>}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Created:</span>
              <p className="font-medium mt-0.5">{format(new Date(assessment.created_at), 'MMM d, yyyy')}</p>
            </div>
            <div>
              <span className="text-gray-500">Last Updated:</span>
              <p className="font-medium mt-0.5">{format(new Date(assessment.updated_at), 'MMM d, yyyy')}</p>
            </div>
          </div>
        )}

        {/* Inline Edit Form (shown when editing) */}
        {isEditingAssessment && (
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
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════
          ZONE B — Threats Overview (hero section)
         ═══════════════════════════════════════════════════════════ */}
      <div className="mb-4">
        {/* Severity summary strip + Add Threat */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Threats ({threats.length})
            </h2>
            {threats.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs">
                {(severityCounts['Critical'] || 0) > 0 && (
                  <span className="px-2 py-0.5 bg-red-600 text-white rounded-full font-semibold">
                    {severityCounts['Critical']} Critical
                  </span>
                )}
                {(severityCounts['High'] || 0) > 0 && (
                  <span className="px-2 py-0.5 bg-amber-500 text-white rounded-full font-semibold">
                    {severityCounts['High']} High
                  </span>
                )}
                {(severityCounts['Medium'] || 0) > 0 && (
                  <span className="px-2 py-0.5 bg-orange-400 text-white rounded-full font-semibold">
                    {severityCounts['Medium']} Medium
                  </span>
                )}
                {(severityCounts['Low'] || 0) > 0 && (
                  <span className="px-2 py-0.5 bg-blue-500 text-white rounded-full font-semibold">
                    {severityCounts['Low']} Low
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setIsThreatModalOpen(true)}>
              <Plus className="w-4 h-4 mr-1" />
              Add Threat
            </Button>
            <button
              onClick={() => setThreatsExpanded(!threatsExpanded)}
              className="p-1.5 text-gray-400 hover:text-gray-600 rounded transition-colors"
            >
              <ChevronDown className={`w-5 h-5 transition-transform ${threatsExpanded ? 'rotate-0' : '-rotate-90'}`} />
            </button>
          </div>
        </div>

        {/* Analyst / AI filter tabs */}
        {threatsExpanded && threats.length > 0 && (
          <>
            <div className="flex items-center gap-1 mb-3">
              {[
                { key: 'all' as const, label: 'All', count: threats.length },
                { key: 'analyst' as const, label: 'Analyst', count: analystThreats.length, icon: UserCheck },
                { key: 'ai' as const, label: 'AI', count: aiThreats.length, icon: Sparkles },
              ].filter(t => t.count > 0).map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setThreatViewTab(tab.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                    threatViewTab === tab.key
                      ? 'bg-gray-900 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {tab.icon && <tab.icon className="w-3 h-3" />}
                  {tab.label}
                  <span className={`ml-0.5 ${threatViewTab === tab.key ? 'text-gray-300' : 'text-gray-400'}`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            {/* Threat cards */}
            <div className="space-y-2">
              {filteredThreats.map((threat) => (
                <ThreatCard
                  key={threat.id}
                  threat={threat}
                  onEdit={openEditThreatModal}
                  onDelete={handleDeleteThreat}
                  onPromote={threat.detected_by === 'ai_intelligence' ? handlePromoteThreat : undefined}
                  showPromote={threat.detected_by === 'ai_intelligence'}
                  recommendations={recommendations.filter(r => r.threat_id === threat.id)}
                  isExpanded={expandedThreats.has(threat.id)}
                  onToggleExpand={() => toggleThreatExpand(threat.id)}
                />
              ))}
            </div>
          </>
        )}

        {threatsExpanded && threats.length === 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
            <AlertTriangle className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-3 text-sm">No threats identified yet</p>
            <Button size="sm" onClick={() => setIsThreatModalOpen(true)}>
              <Plus className="w-4 h-4 mr-1" />
              Add First Threat
            </Button>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════
          ZONE C — Tools & Analysis (collapsible)
         ═══════════════════════════════════════════════════════════ */}
      <div className="bg-white rounded-lg border border-gray-200 mb-4">
        {/* Collapse header */}
        <button
          onClick={() => setToolsExpanded(!toolsExpanded)}
          className="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors rounded-lg"
        >
          <div className="flex items-center gap-2">
            <Wrench className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Tools & Analysis</span>
            <span className="text-xs text-gray-400">{toolsSummary}</span>
          </div>
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${toolsExpanded ? 'rotate-0' : '-rotate-90'}`} />
        </button>

        {toolsExpanded && (
          <>
            {/* Tab navigation */}
            <div className="border-t border-b border-gray-200 px-4">
              <nav className="flex -mb-px gap-1">
                {[
                  { key: 'evidence' as const, label: 'Evidence', icon: FileText, count: evidenceList.length },
                  { key: 'enrichment' as const, label: 'Enrichment', icon: Database },
                  { key: 'ml' as const, label: 'ML Scoring', icon: Brain },
                  { key: 'graph' as const, label: 'Threat Graph', icon: Network },
                  { key: 'cluster' as const, label: 'Clusters', icon: Boxes },
                  { key: 'compliance' as const, label: 'Compliance', icon: Shield },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setAnalyticsTab(tab.key)}
                    className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                      analyticsTab === tab.key
                        ? 'border-primary text-primary'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <tab.icon className="w-3.5 h-3.5" />
                    {tab.label}
                    {'count' in tab && tab.count !== undefined && tab.count > 0 && (
                      <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 rounded-full">{tab.count}</span>
                    )}
                  </button>
                ))}
              </nav>
            </div>

            {/* Tab content */}
            <div className="p-4">
              {/* Evidence Tab */}
              {analyticsTab === 'evidence' && (
                <div>
                  {/* Compact Drop Zone */}
                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors mb-3 ${
                      dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-3">
                      <Upload className="w-5 h-5 text-gray-400" />
                      <p className="text-sm text-gray-500">
                        Drop files here or{' '}
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
                        <span className="text-xs text-gray-400 ml-2">Max {MAX_SIZE_MB}MB</span>
                      </p>
                    </div>
                    {isUploading && (
                      <div className="flex items-center justify-center gap-2 mt-2 text-blue-600">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">Uploading...</span>
                      </div>
                    )}
                    {uploadError && <p className="text-sm text-red-600 mt-2">{uploadError}</p>}
                  </div>

                  {/* Compact Evidence List */}
                  {evidenceList.length > 0 && (
                    <div className="space-y-1">
                      {evidenceList.map((ev) => (
                        <div
                          key={ev.id}
                          className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer group transition-colors"
                          onClick={() => setSelectedEvidence(ev)}
                        >
                          <div className="flex items-center gap-2.5 min-w-0 flex-1">
                            {getStatusIcon(ev.status)}
                            <span className="text-sm text-gray-900 truncate">{ev.file_name}</span>
                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded font-medium shrink-0">
                              {getDocTypeLabel(ev.document_type)}
                            </span>
                            <span className="text-xs text-gray-400 shrink-0">{formatFileSize(ev.size_bytes)}</span>
                            {ev.risk_indicators && (
                              <>
                                {(ev.risk_indicators.critical_vulns ?? 0) > 0 && (
                                  <span className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-600 rounded font-medium shrink-0">
                                    {ev.risk_indicators.critical_vulns} crit
                                  </span>
                                )}
                                {(ev.risk_indicators.high_vulns ?? 0) > 0 && (
                                  <span className="text-[10px] px-1.5 py-0.5 bg-orange-100 text-orange-600 rounded font-medium shrink-0">
                                    {ev.risk_indicators.high_vulns} high
                                  </span>
                                )}
                              </>
                            )}
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                            {ev.status === 'ready' && !ev.analysis_summary && (
                              <button
                                onClick={async () => { try { await apiClient.analyzeEvidence(ev.id); await loadAssessmentData(); } catch {} }}
                                className="p-1 text-gray-400 hover:text-purple-600 rounded"
                                title="Analyze"
                              >
                                <Sparkles className="w-3.5 h-3.5" />
                              </button>
                            )}
                            {ev.status === 'ready' && (
                              <button onClick={() => handleDownloadEvidence(ev.id)} className="p-1 text-gray-400 hover:text-blue-600 rounded" title="Download">
                                <Download className="w-3.5 h-3.5" />
                              </button>
                            )}
                            <button onClick={() => handleDeleteEvidence(ev.id)} className="p-1 text-gray-400 hover:text-red-600 rounded" title="Delete">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {evidenceList.length === 0 && (
                    <p className="text-sm text-gray-400 text-center py-2">
                      Upload vulnerability scans, architecture docs, or other evidence.
                    </p>
                  )}
                </div>
              )}

              {/* Enrichment Tab (merged IntelligencePanel + IntelEnrichmentPanel) */}
              {analyticsTab === 'enrichment' && (
                <div className="space-y-4">
                  <IntelligencePanel
                    assessmentId={assessmentId}
                    onEnrichComplete={loadAssessmentData}
                  />
                  <IntelEnrichmentPanel assessmentId={assessmentId} threatIds={threats.map(t => t.id)} onEnrichComplete={loadAssessmentData} />
                </div>
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
              {analyticsTab === 'compliance' && (
                <CompliancePanel assessmentId={assessmentId} threatIds={threats.map(t => t.id)} />
              )}
            </div>
          </>
        )}
      </div>

      {/* Evidence Detail Modal */}
      {selectedEvidence && (
        <EvidenceDetailModal
          isOpen={!!selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
          evidence={selectedEvidence}
          onDelete={(id) => { setSelectedEvidence(null); handleDeleteEvidence(id); }}
          onRetry={(id) => { setSelectedEvidence(null); handleRetryEvidence(id); }}
          onDownload={(id) => handleDownloadEvidence(id)}
          onAnalyzed={() => loadAssessmentData()}
        />
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
  isExpanded = false,
  onToggleExpand,
}: {
  threat: Threat;
  onEdit: (threat: Threat) => void;
  onDelete: (id: string) => void;
  onPromote?: (id: string, e: React.MouseEvent) => void;
  showPromote?: boolean;
  recommendations?: Recommendation[];
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}) {
  return (
    <div className={`bg-white rounded-lg border transition-all ${isExpanded ? 'border-gray-300 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
      {/* Collapsed row — always visible */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer"
        onClick={onToggleExpand}
      >
        <ChevronRight className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
        <SeverityBadge severity={threat.severity} />
        <h3 className="text-sm font-medium text-gray-900 truncate flex-1">{threat.title}</h3>
        {threat.detected_by === 'ai_intelligence' && <AiBadge />}
        <EnrichmentBadge threatId={threat.id} />
        <MLScoreBadge threatId={threat.id} />
        <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0">
          <span>L: {threat.likelihood}</span>
          <span>I: {threat.impact}</span>
        </div>
        <div className="flex items-center gap-0.5 shrink-0" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => onEdit(threat)}
            className="p-1 text-gray-400 hover:text-blue-600 rounded transition-colors"
            title="Edit"
          >
            <Edit className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(threat.id)}
            className="p-1 text-gray-400 hover:text-red-600 rounded transition-colors"
            title="Delete"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-0 border-t border-gray-100 space-y-3">
          {/* Description */}
          {threat.description && (
            <p className="text-sm text-gray-600 mt-3">{threat.description}</p>
          )}

          {/* Metadata row */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="capitalize">Status: <strong className="text-gray-700">{threat.status.replace('_', ' ')}</strong></span>
            <span>Likelihood: <strong className="text-gray-700">{threat.likelihood}</strong></span>
            <span>Impact: <strong className="text-gray-700">{threat.impact}</strong></span>
            {threat.cve_ids?.length > 0 && <span>CVEs: <strong className="text-gray-700">{threat.cve_ids.length}</strong></span>}
          </div>

          {/* AI Rationale */}
          {threat.ai_rationale && (
            <div className="p-2.5 bg-indigo-50/70 border border-indigo-100 rounded-lg">
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">AI Rationale</span>
              <p className="text-sm text-indigo-900 mt-0.5">{threat.ai_rationale}</p>
            </div>
          )}

          {/* Inline Recommendation */}
          {threat.recommendation && (
            <div className="p-2.5 bg-amber-50/70 border border-amber-100 rounded-lg">
              <div className="flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-amber-600" />
                <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Recommendation</span>
              </div>
              <p className="text-sm text-amber-900 mt-0.5">{threat.recommendation}</p>
            </div>
          )}

          {/* Linked Recommendations */}
          {recommendations.length > 0 && (
            <div className="space-y-2">
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

          {/* Send to Analyst */}
          {showPromote && onPromote && (
            <button
              onClick={(e) => onPromote(threat.id, e)}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-emerald-500 hover:from-indigo-600 hover:to-emerald-600 rounded-lg shadow-sm hover:shadow-md transition-all"
            >
              <ArrowRightCircle className="w-4 h-4" />
              Send to Analyst
            </button>
          )}

          {/* ATT&CK Context */}
          <AttackContextPanel threatId={threat.id} threatTitle={threat.title} />
        </div>
      )}
    </div>
  );
}
