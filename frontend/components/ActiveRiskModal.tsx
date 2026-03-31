'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from './Button';
import { ActiveRisk } from '../lib/types';

interface ActiveRiskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ActiveRiskFormData) => Promise<void>;
  risk: ActiveRisk;
}

export interface ActiveRiskFormData {
  title: string;
  residual_risk: 'Low' | 'Medium' | 'High' | 'Critical';
  mitigation_plan: string;
  risk_status: 'Planned' | 'Ongoing' | 'Delayed' | 'Completed' | 'Accepted';
}

export default function ActiveRiskModal({
  isOpen,
  onClose,
  onSubmit,
  risk,
}: ActiveRiskModalProps) {
  const [formData, setFormData] = useState<ActiveRiskFormData>({
    title: '',
    residual_risk: 'Medium',
    mitigation_plan: '',
    risk_status: 'Planned',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (risk) {
      setFormData({
        title: risk.title,
        residual_risk: risk.residual_risk,
        mitigation_plan: risk.mitigation_plan || '',
        risk_status: risk.risk_status,
      });
    }
  }, [risk]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await onSubmit(formData);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update risk');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const inputClass = "w-full px-3 py-2 bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-colors";

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" onClick={onClose} />
        
        <div className="relative bg-card rounded-xl shadow-xl border border-border max-w-2xl w-full p-6 animate-scale-in">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-foreground">Edit Risk</h2>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Title
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className={inputClass}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Residual Risk
                </label>
                <select
                  value={formData.residual_risk}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      residual_risk: e.target.value as 'Low' | 'Medium' | 'High' | 'Critical',
                    })
                  }
                  className={inputClass}
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Risk Status
                </label>
                <select
                  value={formData.risk_status}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      risk_status: e.target.value as 'Planned' | 'Ongoing' | 'Delayed' | 'Completed' | 'Accepted',
                    })
                  }
                  className={inputClass}
                >
                  <option value="Planned">Planned</option>
                  <option value="Ongoing">Ongoing</option>
                  <option value="Delayed">Delayed</option>
                  <option value="Completed">Completed</option>
                  <option value="Accepted">Accepted</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Mitigation Plan
              </label>
              <textarea
                rows={4}
                value={formData.mitigation_plan}
                onChange={(e) =>
                  setFormData({ ...formData, mitigation_plan: e.target.value })
                }
                className={inputClass}
                placeholder="Describe the mitigation plan..."
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
