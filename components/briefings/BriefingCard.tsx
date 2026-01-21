import { Briefing } from '@/types';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { FileText, Zap, FileSpreadsheet, Calendar } from 'lucide-react';

interface BriefingCardProps {
  briefing: Briefing;
}

const typeIcons = {
  flash: Zap,
  summary: FileSpreadsheet,
  deep: FileText,
  scheduled: Calendar,
};

const typeColors = {
  flash: 'bg-yellow-500/10 text-yellow-400',
  summary: 'bg-blue-500/10 text-blue-400',
  deep: 'bg-purple-500/10 text-purple-400',
  scheduled: 'bg-green-500/10 text-green-400',
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

export function BriefingCard({ briefing }: BriefingCardProps) {
  const Icon = typeIcons[briefing.type];

  return (
    <Card className="hover:border-gray-700 transition-colors cursor-pointer">
      <CardContent className="py-4">
        <div className="flex items-start space-x-4">
          {/* Icon */}
          <div className={`p-2 rounded-lg ${typeColors[briefing.type]}`}>
            <Icon className="w-5 h-5" />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="text-sm font-semibold text-gray-100">{briefing.title}</h4>
                <p className="text-xs text-gray-500 mt-1">{formatTimeAgo(briefing.created_at)}</p>
              </div>
              <div className="flex items-center space-x-2">
                <Badge className="capitalize">{briefing.type}</Badge>
                {!briefing.read && (
                  <div className="w-2 h-2 bg-blue-400 rounded-full" />
                )}
              </div>
            </div>

            {/* Preview */}
            <div className="mt-2 text-sm text-gray-400 line-clamp-2">
              {briefing.content.split('\n').find(line => !line.startsWith('#') && line.trim())}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
