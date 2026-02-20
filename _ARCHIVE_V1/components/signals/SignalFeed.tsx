'use client';

import { mockSignals } from '@/lib/mock-data';
import { SignalCard } from './SignalCard';

export function SignalFeed() {
  return (
    <div className="space-y-3">
      {mockSignals.map((signal) => (
        <SignalCard key={signal.id} signal={signal} />
      ))}
    </div>
  );
}
