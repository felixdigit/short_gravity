import { NextRequest, NextResponse } from "next/server";
import { generateMockSignals } from "@shortgravity/core";

/**
 * GET /api/signals
 *
 * Returns signals in the shape expected by useSignals hook.
 * Currently backed by mock data from @shortgravity/core;
 * swap to Supabase query when live data is wired.
 */
export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const severity = params.get("severity");
  const type = params.get("type");
  const limit = params.get("limit");
  const offset = Number(params.get("offset") ?? 0);

  const coreSignals = generateMockSignals();

  // Map core Signal shape → hook SignalsResponse shape
  let mapped = coreSignals.map((s, i) => ({
    id: i + 1,
    signal_type: s.anomaly_type,
    severity: s.severity,
    category: s.entity_type ?? null,
    title: s.entity_name,
    description:
      typeof s.raw_data?.note === "string" ? s.raw_data.note : null,
    source_refs: [
      {
        table: s.source,
        id: s.entity_id,
        title: s.entity_name,
        date: s.detected_at,
      },
    ],
    metrics: {
      observed_value: s.observed_value,
      baseline_value: s.baseline_value,
      z_score: s.z_score,
      ...s.raw_data,
    },
    confidence_score: s.z_score != null ? Math.min(Math.abs(s.z_score) / 10, 1) : null,
    price_impact_24h: null,
    fingerprint: s.id,
    detected_at: s.detected_at,
    expires_at: new Date(
      new Date(s.detected_at).getTime() + 24 * 3600_000
    ).toISOString(),
    created_at: s.created_at,
  }));

  // Apply filters
  if (severity) mapped = mapped.filter((s) => s.severity === severity);
  if (type) mapped = mapped.filter((s) => s.signal_type === type);

  // Pagination
  const sliced = mapped.slice(offset, limit ? offset + Number(limit) : undefined);

  return NextResponse.json({ data: sliced, count: mapped.length });
}
