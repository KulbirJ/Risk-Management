'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import apiClient from '@/lib/api-client';
import { Assessment } from '@/lib/types';

export default function NewAssessmentPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    system_background: '',
    scope: '',
    tech_stack: '',
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

  return (
    <div className="max-w-3xl mx-auto">
      <Link href="/assessments" className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Assessments
      </Link>

      <h1 className="text-3xl font-bold text-gray-900 mb-2">New Assessment</h1>
      <p className="text-gray-600 mb-8">Create a new threat risk assessment</p>

      {error && (
        <Alert type="error" message={error} onClose={() => setError(null)} />
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="space-y-6">
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Assessment Title *
            </label>
            <input
              type="text"
              id="title"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g., Q1 2024 Web Application Security Assessment"
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Describe the purpose of this assessment..."
            />
          </div>

          <div>
            <label htmlFor="system_background" className="block text-sm font-medium text-gray-700 mb-2">
              System Background
            </label>
            <textarea
              id="system_background"
              value={formData.system_background}
              onChange={(e) => setFormData({ ...formData, system_background: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Provide context about the system being assessed..."
            />
          </div>

          <div>
            <label htmlFor="scope" className="block text-sm font-medium text-gray-700 mb-2">
              Scope
            </label>
            <textarea
              id="scope"
              value={formData.scope}
              onChange={(e) => setFormData({ ...formData, scope: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Define what is included and excluded from this assessment..."
            />
          </div>

          <div>
            <label htmlFor="tech_stack" className="block text-sm font-medium text-gray-700 mb-2">
              Technology Stack
            </label>
            <input
              type="text"
              id="tech_stack"
              value={formData.tech_stack}
              onChange={(e) => setFormData({ ...formData, tech_stack: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g., Python, PostgreSQL, AWS (comma-separated)"
            />
          </div>

          <div>
            <label htmlFor="overall_impact" className="block text-sm font-medium text-gray-700 mb-2">
              Overall Impact *
            </label>
            <select
              id="overall_impact"
              required
              value={formData.overall_impact}
              onChange={(e) => setFormData({ ...formData, overall_impact: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Critical">Critical</option>
            </select>
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
