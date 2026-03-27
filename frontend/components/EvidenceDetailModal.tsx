'use client';

import { useState, useEffect } from 'react';
import {
  X, FileText, Shield, AlertTriangle, Download, RefreshCw,
  Trash2, ChevronDown, ChevronUp, Loader2, Sparkles,
} from 'lucide-react';
import { Button } from './Button';
import { Evidence, RiskIndicators } from '../lib/types';
import apiClient from '../lib/api-client';
import { format } from 'date-fns';

interface EvidenceDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  evidence: Evidence;
  onDelete: (id: string) => void;
  onRetry: (id: string) => void;
  onDownload: (id: string) => void;
  onAnalyzed?: () => void;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  vulnerability_scan: 'Vulnerability Scan',
  architecture_doc: 'Architecture Document',
  network_diagram: 'Network Diagram',
  policy: 'Policy / Compliance',
  config: 'Configuration',
  other: 'Document',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800',
  high: 'bg-orange-100 text-orange-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-green-100 text-green-800',
};

export function EvidenceDetailModal({
  isOpen,
  onClose,
  evidence,
  onDelete,
  onRetry,
  onDownload,
  onAnalyzed,
}: EvidenceDetailModalProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [localEvidence, setLocalEvidence] = useState<Evidence>(evidence);
  const [showExtractedText, setShowExtractedText] = useState(false);
  const [showFindings, setShowFindings] = useState(true);

  useEffect(() => {
    setLocalEvidence(evidence);
    setAnalyzeError(null);
  }, [evidence]);

  if (!isOpen) return null;

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const result = await apiClient.analyzeEvidence(localEvidence.id);
      setLocalEvidence((prev) => ({
        ...prev,
        analysis_summary: result.analysis_summary,
        analysis_findings: result.analysis_findings,
        risk_indicators: result.risk_indicators,
        last_enriched_at: new Date().toISOString(),
      }));
      onAnalyzed?.();
    } catch (err: any) {
      setAnalyzeError(err.response?.data?.detail || err.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const ri = localEvidence.risk_indicators as RiskIndicators | undefined;
  const hasAnalysis = !!localEvidence.analysis_summary;
  const findings = localEvidence.analysis_findings || [];
  const meta = localEvidence.extract_metadata || {};
  const structured = meta.structured || {};

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-start justify-center min-h-screen p-4">
        {/* Backdrop */}
        <div className="fixed inset-0 bg-black/40" onClick={onClose} />

        {/* Modal */}
        <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl my-8">
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-gray-200">
            <div className="flex items-center gap-3 min-w-0">
              <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-gray-900 truncate">
                  {localEvidence.file_name}
                </h2>
                <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                  <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded font-medium">
                    {DOC_TYPE_LABELS[localEvidence.document_type || 'other'] || localEvidence.document_type}
                  </span>
                  {localEvidence.document_type_confidence != null && (
                    <span className="text-gray-400">
                      {localEvidence.document_type_confidence}% confidence
                    </span>
                  )}
                  <span>{formatFileSize(localEvidence.size_bytes)}</span>
                  <span>{format(new Date(localEvidence.created_at), 'MMM d, yyyy')}</span>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 rounded-md"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">
            {/* Analysis Summary */}
            {hasAnalysis ? (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-900 flex items-center gap-1.5 mb-2">
                  <Sparkles className="w-4 h-4" />
                  AI Analysis Summary
                </h3>
                <p className="text-sm text-blue-800 leading-relaxed">
                  {localEvidence.analysis_summary}
                </p>
                {localEvidence.last_enriched_at && (
                  <p className="text-xs text-blue-500 mt-2">
                    Analyzed {format(new Date(localEvidence.last_enriched_at), 'MMM d, yyyy h:mm a')}
                  </p>
                )}
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
                <p className="text-sm text-gray-600 mb-3">
                  This file has not been analyzed by AI yet.
                </p>
                <Button
                  onClick={handleAnalyze}
                  disabled={analyzing || localEvidence.status !== 'ready'}
                  variant="primary"
                  className="text-sm"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-1.5" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-1.5" />
                      Analyze with AI
                    </>
                  )}
                </Button>
                {analyzeError && (
                  <p className="text-xs text-red-600 mt-2">{analyzeError}</p>
                )}
              </div>
            )}

            {/* Risk Indicators */}
            {ri && (
              <div>
                <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-1.5 mb-2">
                  <Shield className="w-4 h-4 text-red-500" />
                  Risk Indicators
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {(ri.critical_vulns ?? 0) > 0 && (
                    <RiskCard label="Critical Vulns" value={ri.critical_vulns!} color="red" />
                  )}
                  {(ri.high_vulns ?? 0) > 0 && (
                    <RiskCard label="High Vulns" value={ri.high_vulns!} color="orange" />
                  )}
                  {(ri.secrets_found ?? 0) > 0 && (
                    <RiskCard label="Secrets Found" value={ri.secrets_found!} color="red" />
                  )}
                  {ri.missing_controls && ri.missing_controls.length > 0 && (
                    <RiskCard label="Missing Controls" value={ri.missing_controls.length} color="amber" />
                  )}
                  {ri.compliance_gaps && ri.compliance_gaps.length > 0 && (
                    <RiskCard label="Compliance Gaps" value={ri.compliance_gaps.length} color="purple" />
                  )}
                  {ri.exposed_services && ri.exposed_services.length > 0 && (
                    <RiskCard label="Exposed Services" value={ri.exposed_services.length} color="orange" />
                  )}
                </div>
                {ri.key_concerns && ri.key_concerns.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {ri.key_concerns.map((concern, i) => (
                      <div key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                        {concern}
                      </div>
                    ))}
                  </div>
                )}
                {ri.missing_controls && ri.missing_controls.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-600 mb-1">Missing Controls:</p>
                    <div className="flex flex-wrap gap-1">
                      {ri.missing_controls.map((ctrl, i) => (
                        <span key={i} className="px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded text-xs">
                          {ctrl}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Structured Metadata */}
            {Object.keys(structured).length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Quick Stats</h3>
                <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-700 space-y-1">
                  {structured.cve_count != null && (
                    <p><span className="font-medium">CVEs detected:</span> {structured.cve_count}</p>
                  )}
                  {structured.host_count != null && (
                    <p><span className="font-medium">Unique hosts:</span> {structured.host_count}</p>
                  )}
                  {structured.scan_tool && structured.scan_tool !== 'unknown' && (
                    <p><span className="font-medium">Scan tool:</span> {structured.scan_tool}</p>
                  )}
                  {structured.frameworks_referenced?.length > 0 && (
                    <p><span className="font-medium">Frameworks:</span> {structured.frameworks_referenced.join(', ')}</p>
                  )}
                  {structured.components_detected?.length > 0 && (
                    <p><span className="font-medium">Components:</span> {structured.components_detected.join(', ')}</p>
                  )}
                  {structured.secrets_found > 0 && (
                    <p className="text-red-700"><span className="font-medium">Potential secrets:</span> {structured.secrets_found}</p>
                  )}
                  {structured.dangerous_settings?.length > 0 && (
                    <p className="text-red-700"><span className="font-medium">Dangerous settings:</span> {structured.dangerous_settings.join(', ')}</p>
                  )}
                </div>
              </div>
            )}

            {/* Findings */}
            {findings.length > 0 && (
              <div>
                <button
                  className="flex items-center gap-1.5 text-sm font-semibold text-gray-900 mb-2 hover:text-gray-700"
                  onClick={() => setShowFindings(!showFindings)}
                >
                  {showFindings ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  Findings ({findings.length})
                </button>
                {showFindings && (
                  <div className="space-y-2">
                    {findings.map((finding: any, i: number) => (
                      <div
                        key={i}
                        className="border border-gray-200 rounded-lg p-3"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[finding.severity] || 'bg-gray-100 text-gray-700'}`}>
                            {finding.severity}
                          </span>
                          <span className="text-sm font-medium text-gray-900 truncate">
                            {finding.vulnerability}
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 line-clamp-2">
                          {finding.description}
                        </p>
                        {finding.cve_ids?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {finding.cve_ids.map((cve: string) => (
                              <span key={cve} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-mono">
                                {cve}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Extracted Text Preview */}
            <div>
              <button
                className="flex items-center gap-1.5 text-sm font-semibold text-gray-900 mb-2 hover:text-gray-700"
                onClick={() => setShowExtractedText(!showExtractedText)}
              >
                {showExtractedText ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                Extracted Text
                {localEvidence.extracted_text && (
                  <span className="text-xs font-normal text-gray-500">
                    ({localEvidence.extracted_text.length.toLocaleString()} chars)
                  </span>
                )}
              </button>
              {showExtractedText && (
                <div className="bg-gray-50 rounded-lg p-3 max-h-60 overflow-y-auto">
                  <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words font-mono">
                    {localEvidence.extracted_text
                      ? localEvidence.extracted_text.slice(0, 3000) +
                        (localEvidence.extracted_text.length > 3000 ? '\n\n… [truncated]' : '')
                      : 'No text extracted'}
                  </pre>
                </div>
              )}
            </div>

            {/* Parser Metadata */}
            {meta.parser && (
              <div className="text-xs text-gray-500 flex flex-wrap gap-3">
                <span>Parser: {meta.parser}</span>
                {meta.page_count != null && <span>Pages: {meta.page_count}</span>}
                {meta.char_count != null && <span>Chars: {meta.char_count.toLocaleString()}</span>}
                {meta.row_count != null && <span>Rows: {meta.row_count}</span>}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between p-4 border-t border-gray-200">
            <div className="flex items-center gap-2">
              {hasAnalysis && (
                <Button onClick={handleAnalyze} disabled={analyzing} variant="secondary" className="text-xs">
                  {analyzing ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <RefreshCw className="w-3.5 h-3.5 mr-1" />}
                  Re-analyze
                </Button>
              )}
              {localEvidence.status === 'ready' && (
                <Button onClick={() => onDownload(localEvidence.id)} variant="secondary" className="text-xs">
                  <Download className="w-3.5 h-3.5 mr-1" />
                  Download
                </Button>
              )}
              {(localEvidence.status === 'processing' || localEvidence.status === 'failed') && (
                <Button onClick={() => onRetry(localEvidence.id)} variant="secondary" className="text-xs">
                  <RefreshCw className="w-3.5 h-3.5 mr-1" />
                  Retry
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => onDelete(localEvidence.id)} variant="danger" className="text-xs">
                <Trash2 className="w-3.5 h-3.5 mr-1" />
                Delete
              </Button>
              <Button onClick={onClose} variant="secondary" className="text-xs">
                Close
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function RiskCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorMap: Record<string, string> = {
    red: 'bg-red-50 text-red-800 border-red-200',
    orange: 'bg-orange-50 text-orange-800 border-orange-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    purple: 'bg-purple-50 text-purple-800 border-purple-200',
  };
  return (
    <div className={`rounded-lg border p-2 text-center ${colorMap[color] || colorMap.amber}`}>
      <p className="text-lg font-bold">{value}</p>
      <p className="text-xs">{label}</p>
    </div>
  );
}

function formatFileSize(bytes?: number) {
  if (!bytes) return 'Unknown size';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
