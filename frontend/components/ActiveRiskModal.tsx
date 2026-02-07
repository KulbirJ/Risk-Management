'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Button } from './Button';
import { ActiveRisk } from '@/lib/types';

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

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black bg-opacity-25" onClick={onClose} />
        
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Edit Risk</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Title
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mitigation Plan
              </label>
              <textarea
                rows={4}
                value={formData.mitigation_plan}
                onChange={(e) =>
                  setFormData({ ...formData, mitigation_plan: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
