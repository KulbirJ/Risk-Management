import axios, { AxiosInstance } from 'axios';
import type { 
  Assessment, 
  ActiveRisk, 
  Threat, 
  Evidence, 
  EvidenceInitResponse,
  AuditLog, 
  Recommendation,
  IntelligenceEnrichRequest,
  IntelligenceEnrichResponse,
  IntelligenceJob,
  IntelligenceStatus,
  AttackTactic,
  AttackTechnique,
  AttackTechniqueSummary,
  ThreatAttackMapping,
  AutoMapResponse,
  KillChain,
  AttackSyncStatus,
  ThreatEnrichRequest,
  ThreatEnrichResponse,
  ThreatEnrichmentsResponse,
  EnrichmentSummary,
  AttackGroup,
  MLModelInfo,
  MLBatchScoreResponse,
  MLScoreResult,
  MLExplanation,
  MLBiasReport,
  MLTrainRequest,
  MLTrainResponse,
  SurvivalCurveResponse,
  SurvivalEstimateResponse,
  AssessmentGraph,
  CriticalNodesResponse,
  NeighbourhoodResponse,
  ClusteringResponse,
  SimilarThreatsResponse,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const axiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
    'X-Tenant-ID': '67636bd3-9846-4bde-806f-aea369fc9457',
    'X-User-ID': '0bc9d6a9-f342-452e-9297-ee33f44d4f84',
  },
});

// API Client with typed methods
class APIClient {
  private client: AxiosInstance;

  constructor(client: AxiosInstance) {
    this.client = client;
  }

  // Assessments
  async getAssessments(params?: { 
    skip?: number; 
    limit?: number; 
    status?: string;
  }): Promise<Assessment[]> {
    const { data } = await this.client.get('/assessments', { params });
    return data;
  }

  async getAssessment(id: string): Promise<Assessment> {
    const { data } = await this.client.get(`/assessments/${id}`);
    return data;
  }

  async createAssessment(payload: Partial<Assessment>): Promise<Assessment> {
    const { data } = await this.client.post('/assessments', payload);
    return data;
  }

  async updateAssessment(id: string, payload: Partial<Assessment>): Promise<Assessment> {
    const { data } = await this.client.patch(`/assessments/${id}`, payload);
    return data;
  }

  async deleteAssessment(id: string): Promise<void> {
    await this.client.delete(`/assessments/${id}`);
  }

  // Active Risks
  async getActiveRisks(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    assessment_id?: string;
  }): Promise<ActiveRisk[]> {
    const { data } = await this.client.get('/active-risks', { params });
    return data;
  }

  async getActiveRisk(id: string): Promise<ActiveRisk> {
    const { data } = await this.client.get(`/active-risks/${id}`);
    return data;
  }

  async createActiveRisk(assessmentId: string, payload: Partial<ActiveRisk>): Promise<ActiveRisk> {
    const { data } = await this.client.post('/active-risks', payload, {
      params: { assessment_id: assessmentId }
    });
    return data;
  }

  async updateActiveRisk(id: string, payload: Partial<ActiveRisk>): Promise<ActiveRisk> {
    const { data } = await this.client.patch(`/active-risks/${id}`, payload);
    return data;
  }

  async acceptRisk(id: string): Promise<ActiveRisk> {
    const { data } = await this.client.post(`/active-risks/${id}/accept`);
    return data;
  }

  async deleteActiveRisk(id: string): Promise<void> {
    await this.client.delete(`/active-risks/${id}`);
  }

  // Threats
  async getThreats(assessmentId: string, params?: {
    skip?: number;
    limit?: number;
  }): Promise<Threat[]> {
    const { data } = await this.client.get('/threats', { 
      params: { ...params, assessment_id: assessmentId } 
    });
    return data;
  }

  async getThreat(id: string): Promise<Threat> {
    const { data } = await this.client.get(`/threats/${id}`);
    return data;
  }

  async createThreat(assessmentId: string, payload: Partial<Threat>): Promise<Threat> {
    const { data } = await this.client.post('/threats', payload, {
      params: { assessment_id: assessmentId }
    });
    return data;
  }

  async updateThreat(id: string, payload: Partial<Threat>): Promise<Threat> {
    const { data } = await this.client.patch(`/threats/${id}`, payload);
    return data;
  }

  async promoteThreat(id: string): Promise<Threat> {
    const { data } = await this.client.post(`/threats/${id}/promote`);
    return data;
  }

  async deleteThreat(id: string): Promise<void> {
    await this.client.delete(`/threats/${id}`);
  }

  // Evidence
  async getEvidence(params?: {
    assessment_id?: string;
    threat_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<Evidence[]> {
    const { data } = await this.client.get('/evidence', { params });
    return data;
  }

  async initiateUpload(assessmentId: string, file: File, documentType?: string): Promise<EvidenceInitResponse> {
    const payload = {
      file_name: file.name,
      content_type: file.type || 'application/octet-stream',
      size_bytes: file.size,
      document_type: documentType || 'other',
    };
    const { data } = await this.client.post('/evidence/initiate', payload, {
      params: { assessment_id: assessmentId },
    });
    return data;
  }

  async uploadToS3(uploadUrl: string, uploadFields: Record<string, string>, file: File): Promise<void> {
    const formData = new FormData();
    Object.entries(uploadFields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append('file', file);

    let response: Response;
    try {
      response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
        mode: 'cors',
      });
    } catch (networkErr) {
      // CORS or network error – fall back to proxy upload through backend
      console.warn('Direct S3 upload failed, using proxy:', networkErr);
      const proxyForm = new FormData();
      proxyForm.append('file', file);
      proxyForm.append('s3_key', uploadFields['key'] || '');
      proxyForm.append('content_type', file.type || 'application/octet-stream');
      const proxyResp = await this.client.post('/evidence/proxy-upload', proxyForm, {
        headers: { 'Content-Type': 'multipart/form-data' },
        maxBodyLength: 10 * 1024 * 1024,
      });
      if (proxyResp.status >= 400) {
        throw new Error(`Proxy upload failed: ${proxyResp.statusText}`);
      }
      return;
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`S3 upload failed (${response.status}): ${text}`);
    }
  }

  async completeUpload(evidenceId: string): Promise<Evidence> {
    const { data } = await this.client.post(`/evidence/${evidenceId}/complete`, {});
    return data;
  }

  async retryEvidence(evidenceId: string): Promise<Evidence> {
    const { data } = await this.client.post(`/evidence/${evidenceId}/retry`, {});
    return data;
  }

  async getDownloadUrl(evidenceId: string): Promise<{ download_url: string; file_name: string }> {
    const { data } = await this.client.get(`/evidence/download/${evidenceId}`);
    return data;
  }

  async deleteEvidence(id: string): Promise<void> {
    await this.client.delete(`/evidence/${id}`);
  }

  // Recommendations
  async getRecommendations(params?: {
    assessment_id?: string;
    threat_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<Recommendation[]> {
    const { data } = await this.client.get('/recommendations', { params });
    return data;
  }

  async createRecommendation(payload: Partial<Recommendation>): Promise<Recommendation> {
    const { data } = await this.client.post('/recommendations', payload);
    return data;
  }

  async updateRecommendation(id: string, payload: Partial<Recommendation>): Promise<Recommendation> {
    const { data } = await this.client.patch(`/recommendations/${id}`, payload);
    return data;
  }

  async deleteRecommendation(id: string): Promise<void> {
    await this.client.delete(`/recommendations/${id}`);
  }

  // Audit Logs
  async getAuditLogs(params?: {
    entity_type?: string;
    entity_id?: string;
    action?: string;
    skip?: number;
    limit?: number;
  }): Promise<AuditLog[]> {
    const { data } = await this.client.get('/audit-logs', { params });
    return data;
  }

  // Threat Catalogue
  async getThreatCatalogue(params?: {
    category?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<any[]> {
    const { data } = await this.client.get('/threat-catalogue', { params });
    return data;
  }

  // Intelligence / AI Enrichment
  async getIntelligenceStatus(): Promise<IntelligenceStatus> {
    const { data } = await this.client.get('/intelligence/status');
    return data;
  }

  async enrichAssessment(assessmentId: string, jobType: string = 'full_enrichment'): Promise<IntelligenceEnrichResponse> {
    const { data } = await this.client.post('/intelligence/enrich', {
      assessment_id: assessmentId,
      job_type: jobType,
    });
    return data;
  }

  async getIntelligenceJobs(params?: {
    assessment_id?: string;
    status?: string;
    limit?: number;
  }): Promise<IntelligenceJob[]> {
    const { data } = await this.client.get('/intelligence/jobs', { params });
    return data;
  }

  async getIntelligenceJob(jobId: string): Promise<IntelligenceJob> {
    const { data } = await this.client.get(`/intelligence/jobs/${jobId}`);
    return data;
  }

  async seedThreatCatalogue(): Promise<any> {
    const { data } = await this.client.post('/intelligence/seed-catalogue');
    return data;
  }

  async resetIntelligenceJobs(assessmentId: string): Promise<any> {
    const { data } = await this.client.post('/intelligence/reset-jobs', null, {
      params: { assessment_id: assessmentId },
    });
    return data;
  }

  // ─── MITRE ATT&CK ───────────────────────────────────────────────

  // Reference data
  async getAttackTactics(): Promise<AttackTactic[]> {
    const { data } = await this.client.get('/attack/tactics');
    return data;
  }

  async getTechniquesByTactic(
    tacticId: string,
    includeSubtechniques = false,
  ): Promise<AttackTechnique[]> {
    const { data } = await this.client.get(
      `/attack/tactics/${tacticId}/techniques`,
      { params: { include_subtechniques: includeSubtechniques } },
    );
    return data;
  }

  async searchAttackTechniques(q: string, limit = 30): Promise<AttackTechniqueSummary[]> {
    const { data } = await this.client.get('/attack/techniques/search', {
      params: { q, limit },
    });
    return data;
  }

  async getAttackTechnique(techniqueId: string): Promise<AttackTechnique> {
    const { data } = await this.client.get(`/attack/techniques/${techniqueId}`);
    return data;
  }

  // Sync
  async getAttackSyncStatus(): Promise<AttackSyncStatus> {
    const { data } = await this.client.get('/attack/sync-status');
    return data;
  }

  async triggerAttackSync(): Promise<AttackSyncStatus> {
    const { data } = await this.client.post('/attack/sync');
    return data;
  }

  // Threat ↔ technique mappings
  async getThreatMappings(threatId: string): Promise<ThreatAttackMapping[]> {
    const { data } = await this.client.get(`/attack/threats/${threatId}/mappings`);
    return data;
  }

  async addThreatMapping(
    threatId: string,
    techniqueId: string,
    confidenceScore = 70,
    mappingRationale?: string,
  ): Promise<ThreatAttackMapping> {
    const { data } = await this.client.post(`/attack/threats/${threatId}/mappings`, {
      technique_id: techniqueId,
      confidence_score: confidenceScore,
      mapping_rationale: mappingRationale,
    });
    return data;
  }

  async autoMapThreat(
    threatId: string,
    options: { save_suggestions?: boolean; confidence_threshold?: number } = {},
  ): Promise<AutoMapResponse> {
    const { data } = await this.client.post(`/attack/threats/${threatId}/auto-map`, {
      save_suggestions: options.save_suggestions ?? true,
      confidence_threshold: options.confidence_threshold ?? 60,
    });
    return data;
  }

  async removeThreatMapping(threatId: string, techniqueId: string): Promise<void> {
    await this.client.delete(`/attack/threats/${threatId}/mappings/${techniqueId}`);
  }

  // Kill chains
  async getKillChains(threatId: string): Promise<KillChain[]> {
    const { data } = await this.client.get(`/attack/threats/${threatId}/kill-chains`);
    return data;
  }

  async generateKillChain(
    threatId: string,
    options: { threat_actor?: string; include_detection_hints?: boolean } = {},
  ): Promise<KillChain> {
    const { data } = await this.client.post(`/attack/threats/${threatId}/kill-chains`, {
      threat_actor: options.threat_actor,
      include_detection_hints: options.include_detection_hints ?? true,
    });
    return data;
  }

  async deleteKillChain(killChainId: string): Promise<void> {
    await this.client.delete(`/attack/kill-chains/${killChainId}`);
  }

  // ─── Phase 1: Intel Enrichment ─────────────────────────────────

  async enrichThreats(body: ThreatEnrichRequest): Promise<ThreatEnrichResponse> {
    const { data } = await this.client.post('/intel/enrich', body);
    return data;
  }

  async getThreatEnrichments(threatId: string): Promise<ThreatEnrichmentsResponse> {
    const { data } = await this.client.get(`/intel/threats/${threatId}/enrichments`);
    return data;
  }

  async getThreatEnrichmentSummary(threatId: string): Promise<EnrichmentSummary> {
    const { data } = await this.client.get(`/intel/threats/${threatId}/summary`);
    return data;
  }

  async getIntelSectors(): Promise<{ sectors: string[] }> {
    const { data } = await this.client.get('/intel/sectors');
    return data;
  }

  async getSectorFrequency(sector: string, catalogueKey: string): Promise<any> {
    const { data } = await this.client.get(`/intel/sectors/${sector}/frequency`, {
      params: { catalogue_key: catalogueKey },
    });
    return data;
  }

  async getAttackGroups(params?: { search?: string; sector?: string; skip?: number; limit?: number }): Promise<{ count: number; groups: AttackGroup[] }> {
    const { data } = await this.client.get('/intel/attack-groups', { params });
    return data;
  }

  async getAttackGroup(groupId: string): Promise<AttackGroup> {
    const { data } = await this.client.get(`/intel/attack-groups/${groupId}`);
    return data;
  }

  // ─── Phase 2: ML Scoring & Survival ────────────────────────────

  async getMLModelInfo(): Promise<MLModelInfo> {
    const { data } = await this.client.get('/ml/model-info');
    return data;
  }

  async trainMLModel(body?: MLTrainRequest): Promise<MLTrainResponse> {
    const { data } = await this.client.post('/ml/train', body || {});
    return data;
  }

  async scoreThreats(body: { assessment_id?: string; threat_ids?: string[]; persist?: boolean }): Promise<MLBatchScoreResponse> {
    const { data } = await this.client.post('/ml/score', body);
    return data;
  }

  async scoreSingleThreat(threatId: string): Promise<MLScoreResult> {
    const { data } = await this.client.get(`/ml/score/${threatId}`);
    return data;
  }

  async explainThreatScore(threatId: string): Promise<MLExplanation> {
    const { data } = await this.client.get(`/ml/explain/${threatId}`);
    return data;
  }

  async getMLBiasReport(): Promise<MLBiasReport> {
    const { data } = await this.client.get('/ml/bias-report');
    return data;
  }

  async estimateSurvival(body: { active_risk_id?: string; assessment_id?: string; persist?: boolean }): Promise<SurvivalEstimateResponse> {
    const { data } = await this.client.post('/ml/survival', body);
    return data;
  }

  async getSurvivalCurve(sector?: string): Promise<SurvivalCurveResponse> {
    const { data } = await this.client.get('/ml/survival/curve', {
      params: sector ? { sector } : undefined,
    });
    return data;
  }

  // ─── Phase 3: Graph Mapping ────────────────────────────────────

  async getAssessmentGraph(assessmentId: string): Promise<AssessmentGraph> {
    const { data } = await this.client.get(`/graph/assessment/${assessmentId}`);
    return data;
  }

  async getCriticalNodes(assessmentId: string, topN = 10): Promise<CriticalNodesResponse> {
    const { data } = await this.client.get(`/graph/assessment/${assessmentId}/critical`, {
      params: { top_n: topN },
    });
    return data;
  }

  async getThreatNeighbourhood(threatId: string, depth = 2): Promise<NeighbourhoodResponse> {
    const { data } = await this.client.get(`/graph/threat/${threatId}/neighbourhood`, {
      params: { depth },
    });
    return data;
  }

  async getShortestPath(assessmentId: string, source: string, target: string): Promise<any> {
    const { data } = await this.client.get(`/graph/assessment/${assessmentId}/path`, {
      params: { source, target },
    });
    return data;
  }

  // ─── Phase 4: Clustering ──────────────────────────────────────

  async clusterAssessment(assessmentId: string, eps = 0.8, minSamples = 2): Promise<ClusteringResponse> {
    const { data } = await this.client.post(`/clusters/assessment/${assessmentId}`, {
      eps, min_samples: minSamples,
    });
    return data;
  }

  async clusterTenant(eps = 0.8, minSamples = 2): Promise<ClusteringResponse> {
    const { data } = await this.client.post('/clusters/tenant', {
      eps, min_samples: minSamples,
    });
    return data;
  }

  async findSimilarThreats(threatId: string, topN = 5): Promise<SimilarThreatsResponse> {
    const { data } = await this.client.get(`/clusters/similar/${threatId}`, {
      params: { top_n: topN },
    });
    return data;
  }
}

export const apiClient = new APIClient(axiosInstance);
export default apiClient;
