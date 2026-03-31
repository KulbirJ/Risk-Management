'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Button } from '../../../components/Button';
import { Alert } from '../../../components/Alert';
import apiClient from '../../../lib/api-client';
import { Assessment } from '../../../lib/types';

export default function NewAssessmentPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    system_background: '',
    scope: '',
    tech_stack: '',
    industry_sector: '',
    overall_impact: 'Medium',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      setError(null);

      const mockUserId = process.env.NEXT_PUBLIC_MOCK_USER_ID || '';
      
      const payload: Partial<Assessment> = {
        title: formData.title,
        description: formData.description || undefined,
        system_background: formData.system_background || undefined,
        scope: formData.scope || undefined,
        tech_stack: formData.tech_stack ? formData.tech_stack.split(',').map(t => t.trim()).filter(t => t) : [],
        industry_sector: formData.industry_sector || undefined,
        overall_impact: formData.overall_impact as 'Low' | 'Medium' | 'High' | 'Critical',
        owner_user_id: mockUserId,
      };

      const assessment = await apiClient.createAssessment(payload);
      router.push(`/assessments/${(assessment as any).id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create assessment');
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors";

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <Link href="/assessments" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Assessments
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">New Assessment</h1>
        <p className="text-muted-foreground mt-1">Create a new threat risk assessment</p>
      </div>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border p-6">
        <div className="space-y-6">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-foreground mb-2">
              Assessment Title *
            </label>
            <input
              type="text"
              id="title"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className={inputClass}
              placeholder="e.g., Q1 2024 Web Application Security Assessment"
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-foreground mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className={inputClass}
              placeholder="Describe the purpose of this assessment..."
            />
          </div>

          <div>
            <label htmlFor="system_background" className="block text-sm font-medium text-foreground mb-2">
              System Background
            </label>
            <textarea
              id="system_background"
              value={formData.system_background}
              onChange={(e) => setFormData({ ...formData, system_background: e.target.value })}
              rows={3}
              className={inputClass}
              placeholder="Provide context about the system being assessed..."
            />
          </div>

          <div>
            <label htmlFor="scope" className="block text-sm font-medium text-foreground mb-2">
              Scope
            </label>
            <textarea
              id="scope"
              value={formData.scope}
              onChange={(e) => setFormData({ ...formData, scope: e.target.value })}
              rows={3}
              className={inputClass}
              placeholder="Define what is included and excluded from this assessment..."
            />
          </div>

          <div>
            <label htmlFor="tech_stack" className="block text-sm font-medium text-foreground mb-2">
              Technology Stack
            </label>
            <input
              type="text"
              id="tech_stack"
              value={formData.tech_stack}
              onChange={(e) => setFormData({ ...formData, tech_stack: e.target.value })}
              className={inputClass}
              placeholder="e.g., Python, PostgreSQL, AWS (comma-separated)"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="industry_sector" className="block text-sm font-medium text-foreground mb-2">
                Industry Sector
              </label>
              <select
                id="industry_sector"
                value={formData.industry_sector}
                onChange={(e) => setFormData({ ...formData, industry_sector: e.target.value })}
                className={inputClass}
              >
                {INDUSTRY_SECTORS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground mt-1">Used for sector-specific threat intelligence</p>
            </div>
            <div>
              <label htmlFor="overall_impact" className="block text-sm font-medium text-foreground mb-2">
                Overall Impact *
              </label>
              <select
                id="overall_impact"
                required
                value={formData.overall_impact}
                onChange={(e) => setFormData({ ...formData, overall_impact: e.target.value })}
                className={inputClass}
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-8">
          <Button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Assessment'}
          </Button>
          <Link href="/assessments">
            <Button type="button" variant="ghost">
              Cancel
            </Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
