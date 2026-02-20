"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { useSignals } from "@/lib/hooks/useSignals";
import type { GlobeSignal } from "@shortgravity/ui";

const Globe = dynamic(
  () => import("@shortgravity/ui").then((mod) => ({ default: mod.Globe })),
  { ssr: false }
);

export function GlobeWidget({ className }: { className?: string }) {
  const { data } = useSignals({ limit: 50 });

  const translatedSignals: GlobeSignal[] = useMemo(() => {
    if (!data?.data) return [];
    return data.data.map((signal) => ({
      id: String(signal.id),
      lat: (Math.random() - 0.5) * 180,
      lng: (Math.random() - 0.5) * 360,
      severity: signal.signal_type,
    }));
    // Intentionally only recompute when signal count changes to avoid
    // random coords shifting on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.data?.length]);

  if (!data) return null;

  return <Globe signals={translatedSignals} className={className} />;
}
