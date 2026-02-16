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
  detected_by: 'scan' | 'diagram' | 'manual' | 'ai';
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
