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
  description: string;
  file_url: string;
  uploaded_at: string;
  uploaded_by: string;
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
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'implemented';
  created_at: string;
}
