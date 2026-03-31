'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from './Button';
import { Threat } from '../lib/types';

interface ThreatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (threat: ThreatFormData) => Promise<void>;
  assessmentId: string;
  threat?: Threat | null;
}

export interface ThreatFormData {
  title: string;
  description: string;
  recommendation: string;
  likelihood: 'Low' | 'Medium' | 'High' | 'Critical';
  impact: 'Low' | 'Medium' | 'High' | 'Critical';
  status?: 'identified' | 'in_review' | 'at_risk' | 'mitigated';
  cve_ids?: string[];
}

export function ThreatModal({ isOpen, onClose, onSubmit, assessmentId, threat }: ThreatModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<ThreatFormData>({
    title: '',
    description: '',
    recommendation: '',
    likelihood: 'Medium',
    impact: 'Medium',
    status: 'identified',
    cve_ids: [],
  });

  const isEditMode = !!threat;

  // Update form data when threat prop changes
  useEffect(() => {
    if (threat) {
      setFormData({
        title: threat.title,
        description: threat.description || '',
        recommendation: threat.recommendation || '',
        likelihood: threat.likelihood,
        impact: threat.impact,
        status: threat.status,
        cve_ids: threat.cve_ids || [],
      });
    } else {
      setFormData({
        title: '',
        description: '',
        recommendation: '',
        likelihood: 'Medium',
        impact: 'Medium',
        status: 'identified',
        cve_ids: [],
      });
    }
    setError(null);
  }, [threat, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await onSubmit(formData);
      if (!isEditMode) {
        setFormData({
          title: '',
          description: '',
          recommendation: '',
          likelihood: 'Medium',
          impact: 'Medium',
          status: 'identified',
          cve_ids: [],
        });
      }
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to ${isEditMode ? 'update' : 'create'} threat`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="bg-card rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-border shadow-xl animate-scale-in">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-foreground">
            {isEditMode ? 'Edit Threat' : 'Add New Threat'}
          </h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
            disabled={loading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 text-red-800 dark:text-red-400 rounded-xl p-3 text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="title" className="block text-sm font-medium text-foreground mb-2">
              Threat Title *
            </label>
            <input
              type="text"
              id="title"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              placeholder="e.g., SQL Injection Attack"
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
              className="w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              placeholder="Describe the threat..."
            />
          </div>

          <div>
            <label htmlFor="recommendation" className="block text-sm font-medium text-foreground mb-2">
              Recommendation
            </label>
            <textarea
              id="recommendation"
              value={formData.recommendation}
              onChange={(e) => setFormData({ ...formData, recommendation: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              placeholder="Recommendation for mitigating this threat..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="likelihood" className="block text-sm font-medium text-foreground mb-2">
                Likelihood *
              </label>
              <select
                id="likelihood"
                required
                value={formData.likelihood}
                onChange={(e) => setFormData({ ...formData, likelihood: e.target.value as any })}
                className="w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>

            <div>
              <label htmlFor="impact" className="block text-sm font-medium text-foreground mb-2">
                Impact *
              </label>
              <select
                id="impact"
                required
                value={formData.impact}
                onChange={(e) => setFormData({ ...formData, impact: e.target.value as any })}
                className="w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>

          {isEditMode && (
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-foreground mb-2">
                Status *
              </label>
              <select
                id="status"
                required
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                className="w-full px-4 py-2 bg-background border border-border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors"
              >
                <option value="identified">Identified</option>
                <option value="in_review">In Review</option>
                <option value="at_risk">At Risk</option>
                <option value="mitigated">Mitigated</option>
              </select>
              {formData.status === 'at_risk' && threat?.status !== 'at_risk' && (
                <p className="mt-2 text-sm text-amber-600">
                  ⚠️ Changing status to "At Risk" will create an entry in the Risk Register.
                </p>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={loading}>
              {loading ? (isEditMode ? 'Saving...' : 'Adding...') : (isEditMode ? 'Save Changes' : 'Add Threat')}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
