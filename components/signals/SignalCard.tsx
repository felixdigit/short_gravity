import { Signal } from '@/types';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { AlertCircle, TrendingUp, Activity, Radio } from 'lucide-react';

interface SignalCardProps {
  signal: Signal;
}

const iconMap = {
  'Orbital Deviation': TrendingUp,
  'Regulatory Filing': AlertCircle,
  'Coverage Gap': Radio,
  'Maneuver Detected': Activity,
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

export function SignalCard({ signal }: SignalCardProps) {
  const Icon = iconMap[signal.anomaly_type as keyof typeof iconMap] || AlertCircle;

  return (
    <Card className="hover:border-gray-700 transition-colors cursor-pointer">
      <CardContent className="py-4">
        <div className="flex items-start space-x-4">
          {/* Icon */}
          <div className={`p-2 rounded-lg ${
            signal.severity === 'critical' ? 'bg-red-500/10' :
            signal.severity === 'high' ? 'bg-orange-500/10' :
            signal.severity === 'medium' ? 'bg-yellow-500/10' :
            'bg-blue-500/10'
          }`}>
            <Icon className={`w-5 h-5 ${
              signal.severity === 'critical' ? 'text-red-400' :
              signal.severity === 'high' ? 'text-orange-400' :
              signal.severity === 'medium' ? 'text-yellow-400' :
              'text-blue-400'
            }`} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h4 className="text-sm font-semibold text-gray-100">{signal.anomaly_type}</h4>
                <p className="text-sm text-gray-400 mt-0.5">{signal.entity_name}</p>
              </div>
              <Badge severity={signal.severity}>
                {signal.severity.toUpperCase()}
              </Badge>
            </div>

            {/* Metrics */}
            {signal.observed_value !== undefined && signal.baseline_value !== undefined && (
              <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                <span>
                  Observed: <span className="text-gray-300">{signal.observed_value.toFixed(2)}</span>
                </span>
                <span>
                  Baseline: <span className="text-gray-300">{signal.baseline_value.toFixed(2)}</span>
                </span>
                {signal.z_score && (
                  <span>
                    Z-score: <span className="text-gray-300">{signal.z_score.toFixed(1)}σ</span>
                  </span>
                )}
              </div>
            )}

            {/* Footer */}
            <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
              <span>{formatTimeAgo(signal.detected_at)}</span>
              {!signal.processed && (
                <span className="text-blue-400">Awaiting analysis</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
