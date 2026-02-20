'use client';

import { mockBriefings } from '@/lib/mock-data';
import { BriefingCard } from './BriefingCard';

export function BriefingList() {
  return (
    <div className="space-y-3">
      {mockBriefings.map((briefing) => (
        <BriefingCard key={briefing.id} briefing={briefing} />
      ))}
    </div>
  );
}
