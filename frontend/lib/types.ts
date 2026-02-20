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
  quality?: string;
  created_at: string;
}

export interface EvidenceInitResponse {
  evidence_id: string;
  upload_url: string;
  upload_fields: Record<string, string>;
  s3_key: string;
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
