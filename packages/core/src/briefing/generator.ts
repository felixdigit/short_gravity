/**
 * Briefing Generator — Pure prompt builders and output types.
 *
 * No API calls. No SDK imports. Just string assembly and type contracts
 * for the Claude-powered briefing pipeline.
 */

import type { AnomalyType, Severity } from "../signals/analyzer";

// ─── Domain Types ───────────────────────────────────────────────────────────

export interface EntityProfile {
  id: string;
  type: "company" | "satellite" | "constellation" | "filing";
  name: string;

  company?: {
    ticker?: string;
    sector: string;
    marketCap?: number;
    description: string;
    keyPeople: Array<{ name: string; role: string }>;
    recentFilings: Array<{ type: string; date: string; summary: string }>;
    competitors: string[];
  };

  satellite?: {
    noradId: string;
    constellation?: string;
    operator: string;
    launchDate: string;
    orbitType: "LEO" | "MEO" | "GEO" | "HEO";
    purpose: string;
    currentStatus:
      | "operational"
      | "maneuvering"
      | "decommissioned"
      | "unknown";
  };

  signalHistory: Array<{
    date: string;
    type: string;
    summary: string;
  }>;

  inWatchlist: boolean;
  userNotes?: string;
}

export interface SignalInput {
  anomalyType: AnomalyType;
  severity: Severity;
  entityId: string;
  entityType: string;
  entityName: string;
  metricType: string;
  observedValue: number | null;
  baselineValue: number | null;
  zScore: number | null;
  rawData: Record<string, unknown>;
}

export interface SignalContextBundle {
  primarySignal: SignalInput;
  relatedSignals: SignalInput[];

  entityProfile: EntityProfile;

  orbitalContext?: {
    currentPosition: {
      latitude: number;
      longitude: number;
      altitude: number;
    };
    recentManeuvers: Array<{ date: string; deltaV: number }>;
    conjunctionRisk: Array<{
      objectId: string;
      tca: string;
      missDistance: number;
    }>;
    coverageStatus: { percentGlobalCoverage: number };
  };

  marketContext?: {
    currentPrice: number;
    priceChange24h: number;
    volume: number;
    volumeVsAvg: number;
    recentNews: Array<{
      headline: string;
      source: string;
      date: string;
    }>;
  };

  userContext: {
    watchlistPriority: "high" | "medium" | "low" | null;
    customAlertThresholds?: Record<string, number>;
    preferredBriefingStyle: "technical" | "executive" | "balanced";
  };
}

// ─── Structured Output ──────────────────────────────────────────────────────

export type Implication =
  | "bullish"
  | "bearish"
  | "neutral"
  | "operational_concern";
export type Confidence = "high" | "medium" | "low";

export interface StructuredAnalysis {
  situation: string;
  analysis: {
    technical: string;
    historical: string;
    crossDomain: string;
  };
  assessment: {
    implication: Implication;
    confidence: Confidence;
    rationale: string;
  };
  watchItems: string[];
}

export type BriefingType = "flash" | "summary" | "deep" | "scheduled";

// ─── Prompt Builders ────────────────────────────────────────────────────────

/**
 * Build a flash alert prompt (2-3 sentence real-time alert).
 */
export function buildFlashAlertPrompt(bundle: SignalContextBundle): string {
  const { primarySignal, entityProfile } = bundle;
  const history = entityProfile.signalHistory
    .slice(0, 3)
    .map(
      (s) => `- ${s.date}: ${s.summary}`,
    )
    .join("\n");

  return `You are a space economy intelligence analyst. Generate a brief, actionable alert for this anomaly.

## SIGNAL
Type: ${primarySignal.anomalyType}
Severity: ${primarySignal.severity}
Entity: ${entityProfile.name} (${entityProfile.type})
Observed: ${primarySignal.observedValue} (baseline: ${primarySignal.baselineValue})
Z-Score: ${primarySignal.zScore?.toFixed(2) ?? "N/A"}

## ENTITY CONTEXT
${entityProfile.company?.description || entityProfile.satellite?.purpose || "No additional context."}

## RECENT HISTORY
${history || "No prior signals."}

## INSTRUCTIONS
Generate a 2-3 sentence alert that:
1. States what happened in plain language
2. Notes why it matters (deviation from normal)
3. Suggests immediate relevance (bullish/bearish/neutral signal or operational concern)

Do NOT use headers or bullet points. Write in concise analyst prose.`;
}

/**
 * Build a deep analysis prompt (500-1500 word intelligence brief).
 */
export function buildDeepAnalysisPrompt(
  bundle: SignalContextBundle,
): string {
  const relatedList = bundle.relatedSignals
    .map(
      (s) =>
        `- [${s.severity}] ${s.anomalyType}: ${s.observedValue}`,
    )
    .join("\n");

  return `You are a senior space economy analyst preparing an intelligence brief for institutional investors.

## PRIMARY SIGNAL
${JSON.stringify(bundle.primarySignal, null, 2)}

## ENTITY PROFILE
${JSON.stringify(bundle.entityProfile, null, 2)}

## ORBITAL CONTEXT
${bundle.orbitalContext ? JSON.stringify(bundle.orbitalContext, null, 2) : "N/A"}

## MARKET CONTEXT
${bundle.marketContext ? JSON.stringify(bundle.marketContext, null, 2) : "N/A"}

## RELATED SIGNALS (last 7 days)
${relatedList || "None."}

## USER PREFERENCE
Briefing style: ${bundle.userContext.preferredBriefingStyle}

---

Generate a structured intelligence brief with:

1. **SITUATION** (2-3 sentences): What happened and when
2. **ANALYSIS** (2-3 paragraphs):
   - Technical explanation of the anomaly
   - Historical context and pattern recognition
   - Cross-domain implications (regulatory <-> physical <-> market)
3. **ASSESSMENT** (1 paragraph): Investment/strategic implications with confidence level
4. **WATCH ITEMS** (3-5 bullets): Specific follow-up indicators to monitor

Maintain analytical rigor. Avoid speculation without evidence. Cite specific data points.`;
}

/**
 * Build a prompt that requests StructuredAnalysis JSON output.
 */
export function buildStructuredAnalysisPrompt(
  bundle: SignalContextBundle,
): string {
  return `${buildDeepAnalysisPrompt(bundle)}

---

IMPORTANT: Return your analysis as valid JSON matching this schema:
{
  "situation": "string",
  "analysis": {
    "technical": "string",
    "historical": "string",
    "crossDomain": "string"
  },
  "assessment": {
    "implication": "bullish" | "bearish" | "neutral" | "operational_concern",
    "confidence": "high" | "medium" | "low",
    "rationale": "string"
  },
  "watchItems": ["string"]
}`;
}

/**
 * Build a weekly/scheduled report prompt.
 */
export function buildScheduledReportPrompt(
  watchlistSignals: SignalInput[],
  portfolioEntities: EntityProfile[],
): string {
  const signalBlocks = watchlistSignals
    .map(
      (s) => `### ${s.entityName}
- Signal: ${s.anomalyType} (${s.severity})
- Deviation: ${s.zScore?.toFixed(1) ?? "?"}σ from baseline
- Raw: ${JSON.stringify(s.rawData)}`,
    )
    .join("\n\n");

  const entityBlocks = portfolioEntities
    .map(
      (e) => `### ${e.name}
- Type: ${e.type}
- Recent signals: ${e.signalHistory.length}
- Status: ${e.satellite?.currentStatus || e.company?.sector || "unknown"}`,
    )
    .join("\n\n");

  return `You are preparing a weekly intelligence summary for a space economy investor.

## WATCHLIST ACTIVITY (past 7 days)
${signalBlocks || "No activity."}

## PORTFOLIO ENTITIES
${entityBlocks || "None tracked."}

---

Generate a weekly intelligence summary with:

1. **EXECUTIVE SUMMARY** (3-4 sentences): Week's most important developments
2. **KEY SIGNALS BY CATEGORY**:
   - Regulatory developments
   - Orbital/operational changes
   - Market movements
3. **PORTFOLIO HEALTH**: Status of tracked assets
4. **FORWARD LOOK**: Upcoming events to watch (launches, filings, earnings)

Keep tone professional and data-driven. Prioritize actionable insights.`;
}
