export interface ActiveRisk {
  id: string;
  tenant_id: string;
  assessment_id: string;
  threat_id: string;
  title: string;
  residual_risk: 'Low' | 'Medium' | 'High' | 'Critical';
  risk_owner_id: string;
  mitigation_plan?: string;
  acceptance_date?: string;
  review_cycle_days: number;
  status: 'open' | 'accepted' | 'mitigating' | 'closed';
  risk_status: 'Planned' | 'Ongoing' | 'Delayed' | 'Completed' | 'Accepted';
  detected_by?: string;
  ai_rationale?: string;
  risk_score?: number;
  likelihood?: string;
  impact?: string;
  created_at: string;
  updated_at: string;
}

export interface Assessment {
  id: string;
  tenant_id: string;
  title: string;
  description?: string;
  system_background?: string;
  scope?: string;
  tech_stack: string[];
  industry_sector?: string;
  overall_impact: 'Low' | 'Medium' | 'High' | 'Critical';
  status: 'draft' | 'in_review' | 'completed' | 'archived';
  owner_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface Threat {
  id: string;
  tenant_id: string;
  assessment_id: string;
  catalogue_key?: string;
  title: string;
  description?: string;
  recommendation?: string;
  detected_by: 'scan' | 'diagram' | 'manual' | 'ai' | 'ai_intelligence' | 'analyst_assessed';
  cve_ids: string[];
  cvss_score?: string;
  likelihood: 'Low' | 'Medium' | 'High' | 'Critical';
  likelihood_score: number;
  impact: 'Low' | 'Medium' | 'High' | 'Critical';
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  status: 'identified' | 'in_review' | 'at_risk' | 'mitigated';
  ai_rationale?: string;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
}

export interface RiskIndicators {
  critical_vulns?: number;
  high_vulns?: number;
  exposed_services?: string[];
  missing_controls?: string[];
  compliance_gaps?: string[];
  secrets_found?: number;
  key_concerns?: string[];
}

export interface Evidence {
  id: string;
  assessment_id: string;
  threat_id?: string;
  uploaded_by_id?: string;
  file_name: string;
  mime_type?: string;
  size_bytes?: number;
  s3_key?: string;
  status: 'processing' | 'ready' | 'failed';
  extracted_text?: string;
  extract_metadata?: Record<string, any>;
  document_type?: string;
  document_type_confidence?: number;
  quality?: string;
  analysis_summary?: string;
  analysis_findings?: Array<Record<string, any>>;
  risk_indicators?: RiskIndicators;
  last_enriched_at?: string;
  created_at: string;
}

export interface EvidenceInitResponse {
  evidence_id: string;
  upload_url: string;
  upload_fields: Record<string, string>;
  s3_key: string;
  /** 'PUT' = presigned PUT (binary body); 'POST' = legacy multipart form */
  upload_method?: 'PUT' | 'POST';
}

export interface AuditLog {
  id: string;
  tenant_id: string;
  actor_user_id?: string;
  action_type: string;
  resource_type: string;
  resource_id: string;
  changes?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  text?: string;
  type?: string;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'implemented';
  ai_generated?: boolean;
  estimated_effort?: string;
  cost_estimate?: string;
  active_risk_id?: string;
  assessment_id?: string;
  threat_id?: string;
  created_at: string;
}

// Intelligence / AI Enrichment types
export interface IntelligenceEnrichRequest {
  assessment_id: string;
  job_type?: 'full_enrichment' | 'vulnerability_scan' | 'threat_mapping';
}

export interface IntelligenceEnrichResponse {
  job_id: string;
  assessment_id: string;
  status: string;
  vulnerabilities_identified: number;
  threats_mapped: number;
  risks_created: number;
  recommendations_generated: number;
  errors: string[];
  model_used?: string;
  started_at?: string;
  completed_at?: string;
}

export interface IntelligenceJob {
  id: string;
  assessment_id: string;
  initiated_by_id: string;
  status: string;
  job_type: string;
  model_id?: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  results?: Record<string, any>;
  created_at: string;
}

/** One step inside a full-assessment-run job's results. */
export interface FullRunStep {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message: string;
  percent_end: number;
}

/** Shape of IntelligenceJob.results for job_type="full_assessment_run". */
export interface FullRunResults {
  steps: FullRunStep[];
  percent_complete: number;
}

export interface IntelligenceStatus {
  bedrock_enabled: boolean;
  primary_model: string;
  fallback_model: string;
  bedrock_region: string;
  confidence_threshold: number;
}

// ─────────────────────────────────────────────────────────────────
// MITRE ATT&CK Types
// ─────────────────────────────────────────────────────────────────

export interface AttackTactic {
  id: string;
  stix_id: string;
  mitre_id: string;
  name: string;
  shortname: string;
  description?: string;
  url?: string;
  phase_order?: number;
  technique_count?: number;
}

export interface AttackTechnique {
  id: string;
  stix_id: string;
  mitre_id: string;
  name: string;
  tactic_id?: string;
  tactic_shortname?: string;
  description?: string;
  detection_text?: string;
  platforms: string[];
  data_sources: string[];
  mitigations: string[];
  url?: string;
  is_subtechnique: boolean;
  is_deprecated: boolean;
}

export interface AttackTechniqueSummary {
  id: string;
  mitre_id: string;
  name: string;
  tactic_shortname?: string;
  is_subtechnique: boolean;
}

export interface ThreatAttackMapping {
  id: string;
  threat_id: string;
  technique_id: string;
  technique: AttackTechnique;
  confidence_score: number;
  auto_mapped: boolean;
  mapping_rationale?: string;
  created_at: string;
}

export interface AutoMapSuggestion {
  technique_id?: string;
  mitre_id: string;
  technique_name: string;
  confidence_score: number;
  mapping_rationale: string;
  tactic_shortname?: string;
}

export interface AutoMapResponse {
  suggestions: AutoMapSuggestion[];
  saved_count: number;
  threat_id: string;
}

export interface KillChainStage {
  id: string;
  stage_number: number;
  tactic_name: string;
  technique_name?: string;
  mitre_id?: string;
  description?: string;
  actor_behavior?: string;
  detection_hint?: string;
}

export interface KillChain {
  id: string;
  threat_id: string;
  tenant_id: string;
  scenario_name: string;
  description?: string;
  threat_actor?: string;
  generated_by_ai: boolean;
  model_id?: string;
  status: 'building' | 'complete' | 'failed';
  stages: KillChainStage[];
  created_at: string;
}

export interface AttackSyncStatus {
  id?: string;
  sync_status: 'never' | 'running' | 'completed' | 'failed';
  last_synced_at?: string;
  tactics_count: number;
  techniques_count: number;
  source_url?: string;
  error_message?: string;
}

// ─────────────────────────────────────────────────────────────────
// Phase 1: Intel Enrichment Types
// ─────────────────────────────────────────────────────────────────

export interface ThreatEnrichRequest {
  assessment_id?: string;
  threat_ids?: string[];
  force_refresh?: boolean;
}

export interface ThreatEnrichResponse {
  status: string;
  threats_enriched: number;
  results?: Record<string, any>;
  errors?: string[];
}

export interface EnrichmentRecord {
  id: string;
  source: string;
  source_id?: string;
  severity_score?: number;
  feature_vector?: Record<string, any>;
  fetched_at?: string;
  expires_at?: string;
  is_stale?: boolean;
}

export interface ThreatEnrichmentsResponse {
  threat_id: string;
  enrichment_count: number;
  enrichments: EnrichmentRecord[];
}

export interface EnrichmentSummary {
  threat_id: string;
  total_sources: number;
  highest_severity: number;
  sources: string[];
  last_enriched?: string;
}

export interface AttackGroup {
  id: string;
  stix_id?: string;
  name: string;
  aliases: string[];
  description?: string;
  technique_count: number;
  target_sectors: string[];
  first_seen?: string;
  last_seen?: string;
  url?: string;
}

// ─────────────────────────────────────────────────────────────────
// Phase 2: ML Scoring & Survival Types
// ─────────────────────────────────────────────────────────────────

export interface MLModelInfo {
  trained: boolean;
  feature_count: number;
  algorithm?: string;
  trained_at?: string;
  training_samples?: number;
  feature_keys?: string[];
  metrics?: Record<string, number>;
}

export interface MLScoreResult {
  threat_id: string;
  score: number;
  confidence?: number;
  features_used?: string[];
  scored_at?: string;
}

export interface MLBatchScoreResponse {
  scored: number;
  results: MLScoreResult[];
  errors?: string[];
}

export interface MLExplanationComponent {
  feature: string;
  value: number;
  points: number;
  max: number;
}

export interface MLExplanation {
  threat_id: string;
  threat_title?: string;
  likelihood_score?: number;
  method?: string;
  components: MLExplanationComponent[];
  total_points: number;
  max_possible: number;
}

export interface MLBiasSectorStats {
  count: number;
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
  quartiles?: Record<string, number>;
}

export interface MLBiasReport {
  sectors: Record<string, MLBiasSectorStats>;
  total_threats: number;
  generated_at?: string;
}

export interface MLTrainRequest {
  algorithm?: string;
  min_samples?: number;
}

export interface MLTrainResponse {
  status: string;
  algorithm: string;
  samples: number;
  accuracy?: number;
  feature_importances?: Record<string, number>;
}

export interface SurvivalCurvePoint {
  time_days: number;
  probability: number;
}

export interface SurvivalCurveResponse {
  method?: string;
  sector?: string | null;
  median_survival_days?: number;
  timeline_days: number[];
  survival_probability: number[];
  n_observations?: number;
  n_events?: number;
  note?: string;
}

export interface SurvivalEstimateResponse {
  estimated_count: number;
  estimates: {
    active_risk_id: string;
    estimated_persistence_days: number;
    confidence?: number;
  }[];
}

// ─────────────────────────────────────────────────────────────────
// Phase 3: Graph Mapping Types
// ─────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  severity?: string;
  score?: number;
  pagerank?: number;
  betweenness?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  weight?: number;
}

export interface GraphStats {
  node_count: number;
  edge_count: number;
  density?: number;
  components?: number;
}

export interface AssessmentGraph {
  assessment_id?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  pagerank?: Record<string, number>;
  stats: GraphStats;
}

export interface CriticalNode {
  id: string;
  label: string;
  type: string;
  pagerank: number;
  betweenness: number;
  composite_score: number;
}

export interface CriticalNodesResponse {
  assessment_id: string;
  critical_nodes: CriticalNode[];
  total_nodes?: number;
}

export interface NeighbourhoodResponse {
  threat_id: string;
  depth: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ─────────────────────────────────────────────────────────────────
// Phase 4: Clustering Types
// ─────────────────────────────────────────────────────────────────

export interface ClusterThreat {
  threat_id: string;
  title?: string;
  cluster_id: number;
  is_outlier: boolean;
  likelihood_score?: number;
  severity?: string;
}

export interface ClusterQuality {
  n_clusters: number;
  n_outliers: number;
  n_threats: number;
  silhouette_score?: number;
}

export interface ClusteringResponse {
  scope: string;
  clusters_found: number;
  quality: ClusterQuality;
  threats: ClusterThreat[];
}

export interface SimilarThreat {
  threat_id: string;
  title: string;
  similarity: number;
  assessment_id?: string;
}

export interface SimilarThreatsResponse {
  target_threat_id: string;
  target_title?: string;
  similar_threats: SimilarThreat[];
}

// ─────────────────────────────────────────────────────────────────
// Report Types
// ─────────────────────────────────────────────────────────────────

export interface KillChainStageReport {
  stage_number: number;
  tactic_name: string;
  technique_name?: string;
  mitre_id?: string;
  actor_behavior?: string;
  detection_hint?: string;
}

export interface KillChainReport {
  id: string;
  scenario_name: string;
  threat_actor?: string;
  description?: string;
  stages: KillChainStageReport[];
}

export interface AttackMappingReport {
  mitre_id: string;
  technique_name: string;
  tactic_shortname?: string;
  confidence_score: number;
  mapping_rationale?: string;
}

export interface ThreatReportItem {
  id: string;
  title: string;
  description?: string;
  recommendation?: string;
  catalogue_key?: string;
  cve_ids: string[];
  cvss_score?: string;
  likelihood: string;
  impact: string;
  severity: string;
  status: string;
  likelihood_score: number;
  likelihood_label: string;
  top_factors: Array<{ feature?: string; value?: number; weight?: number; contribution?: number; [key: string]: any }>;
  intel_sources: string[];
  cve_data: Record<string, any>;
  otx_data: Record<string, any>;
  exploit_data: Record<string, any>;
  sector_frequency: Record<string, any>;
  attack_groups: Array<Record<string, any>>;
  attack_mappings: AttackMappingReport[];
  kill_chains: KillChainReport[];
  recommendations: Array<{ id: string; title?: string; description: string; type: string; priority: string; status: string }>;
}

export interface AssessmentReportStats {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  mitigated: number;
  at_risk: number;
  enriched: number;
  with_exploits: number;
  with_kill_chains: number;
}

export interface AssessmentReport {
  assessment_id: string;
  assessment_title: string;
  assessment_description?: string;
  industry_sector?: string;
  overall_impact: string;
  generated_at: string;
  stats: AssessmentReportStats;
  top_risks: ThreatReportItem[];
  threats: ThreatReportItem[];
}
