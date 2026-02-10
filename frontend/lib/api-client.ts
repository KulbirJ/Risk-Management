import axios, { AxiosInstance } from 'axios';
import type { 
  Assessment, 
  ActiveRisk, 
  Threat, 
  Evidence, 
  AuditLog, 
  Recommendation 
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

  async createEvidence(payload: Partial<Evidence>): Promise<Evidence> {
    const { data } = await this.client.post('/evidence', payload);
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
}

export const apiClient = new APIClient(axiosInstance);
export default apiClient;
