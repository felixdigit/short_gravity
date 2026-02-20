# Briefing Architecture

**Component:** The Briefing  
**Function:** Strategic Context Synthesis  
**Version:** 1.0

---

## Overview

The Briefing is the synthesis layer that transforms raw Signals from the Engine and Verification from the Cockpit into high-signal intelligence reports. It translates detected anomalies into investment or strategic implications using Claude as the reasoning engine.

---

## Synthesis Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BRIEFING PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

   Input Collection          Context Assembly         Generation          Output
   ────────────────          ────────────────         ──────────          ──────

┌───────────────┐         ┌───────────────────┐     ┌───────────────┐
│   Signals     │────┐    │                   │     │               │
│   (Anomalies) │    │    │   Entity Profile  │     │   Claude API  │
└───────────────┘    │    │   - Company data  │     │   (Opus/Sonnet)│
                     ├───▶│   - Satellite info│────▶│               │
┌───────────────┐    │    │   - Historical    │     │   Structured  │
│   Cockpit     │────┘    │     context       │     │   Prompting   │
│   (Positions) │         │                   │     │               │
└───────────────┘         └───────────────────┘     └───────┬───────┘
                                                            │
┌───────────────┐                                           │
│   User        │                                           │
│   Watchlist   │──────────────────────────────────────────▶│
│   & Prefs     │                                           │
└───────────────┘                                           │
                                                            ▼
                          ┌──────────────────────────────────────────────┐
                          │              BRIEFING OUTPUT                  │
                          │  ┌────────────────┐  ┌────────────────────┐  │
                          │  │  Flash Alert   │  │  Deep Analysis     │  │
                          │  │  (Push/Real-   │  │  (On-demand        │  │
                          │  │   time)        │  │   report)          │  │
                          │  └────────────────┘  └────────────────────┘  │
                          └──────────────────────────────────────────────┘
```

---

## Briefing Types

| Type | Trigger | Length | Latency | Use Case |
|------|---------|--------|---------|----------|
| **Flash Alert** | High-severity signal | 2-3 sentences | <5s | Push notification, real-time dashboard |
| **Signal Summary** | Batch of related signals | 1-2 paragraphs | <15s | Daily digest, signal feed |
| **Deep Analysis** | User request or critical event | 500-1500 words | 30-60s | Investment memo, strategic brief |
| **Scheduled Report** | Cron (daily/weekly) | 2-4 pages | Background | Portfolio summary, watchlist review |

---

## Context Assembly

Before prompting Claude, assemble all relevant context for the entity/event.

### Entity Profile Schema

```typescript
interface EntityProfile {
  // Core identity
  id: string;
  type: 'company' | 'satellite' | 'constellation' | 'filing';
  name: string;
  
  // Company-specific
  company?: {
    ticker?: string;
    sector: string;
    marketCap?: number;
    description: string;
    keyPeople: Array<{ name: string; role: string }>;
    recentFilings: Array<{ type: string; date: Date; summary: string }>;
    competitors: string[];
  };
  
  // Satellite-specific
  satellite?: {
    noradId: string;
    constellation?: string;
    operator: string;
    launchDate: Date;
    orbitType: 'LEO' | 'MEO' | 'GEO' | 'HEO';
    purpose: string;
    currentStatus: 'operational' | 'maneuvering' | 'decommissioned' | 'unknown';
  };
  
  // Historical context
  signalHistory: Array<{
    date: Date;
    type: string;
    summary: string;
  }>;
  
  // User context
  inWatchlist: boolean;
  userNotes?: string;
}

async function assembleEntityProfile(
  entityId: string,
  entityType: string,
  supabase: SupabaseClient
): Promise<EntityProfile> {
  // Fetch from multiple tables
  const [entity, signals, filings] = await Promise.all([
    supabase.from('entities').select('*').eq('id', entityId).single(),
    supabase.from('signals').select('*').eq('entity_id', entityId).order('created_at', { ascending: false }).limit(10),
    supabase.from('filings').select('*').eq('entity_id', entityId).order('filed_at', { ascending: false }).limit(5),
  ]);
  
  // Assemble profile
  return {
    ...entity.data,
    signalHistory: signals.data,
    recentFilings: filings.data,
  };
}
```

### Signal Context Bundle

```typescript
interface SignalContextBundle {
  // The triggering signal(s)
  primarySignal: Signal;
  relatedSignals: Signal[];
  
  // Entity context
  entityProfile: EntityProfile;
  
  // Orbital context (if applicable)
  orbitalContext?: {
    currentPosition: SatellitePosition;
    recentManeuvers: Array<{ date: Date; deltaV: number }>;
    conjunctionRisk: Array<{ objectId: string; tca: Date; missDistance: number }>;
    coverageStatus: { percentGlobalCoverage: number };
  };
  
  // Market context (if applicable)
  marketContext?: {
    currentPrice: number;
    priceChange24h: number;
    volume: number;
    volumeVsAvg: number;
    recentNews: Array<{ headline: string; source: string; date: Date }>;
  };
  
  // User context
  userContext: {
    watchlistPriority: 'high' | 'medium' | 'low' | null;
    customAlertThresholds?: Record<string, number>;
    preferredBriefingStyle: 'technical' | 'executive' | 'balanced';
  };
}
```

---

## Claude Integration

### API Configuration

```typescript
// lib/claude/client.ts
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export const MODELS = {
  FLASH: 'claude-sonnet-4-20250514',      // Fast, for real-time alerts
  DEEP: 'claude-sonnet-4-20250514',      // Quality, for analysis (or Opus for critical)
} as const;

export async function generateBriefing(
  prompt: string,
  model: keyof typeof MODELS = 'FLASH',
  maxTokens: number = 1024
): Promise<string> {
  const response = await anthropic.messages.create({
    model: MODELS[model],
    max_tokens: maxTokens,
    messages: [{ role: 'user', content: prompt }],
  });
  
  return response.content[0].type === 'text' 
    ? response.content[0].text 
    : '';
}
```

### Prompt Templates

#### Flash Alert Prompt

```typescript
// lib/claude/prompts/flash-alert.ts
export function buildFlashAlertPrompt(bundle: SignalContextBundle): string {
  return `You are a space economy intelligence analyst. Generate a brief, actionable alert for this anomaly.

## SIGNAL
Type: ${bundle.primarySignal.anomalyType}
Severity: ${bundle.primarySignal.severity}
Entity: ${bundle.entityProfile.name} (${bundle.entityProfile.type})
Observed: ${bundle.primarySignal.observedValue} (baseline: ${bundle.primarySignal.baselineValue})
Z-Score: ${bundle.primarySignal.zScore.toFixed(2)}

## ENTITY CONTEXT
${bundle.entityProfile.company?.description || bundle.entityProfile.satellite?.purpose}

## RECENT HISTORY
${bundle.entityProfile.signalHistory.slice(0, 3).map(s => `- ${s.date.toISOString().split('T')[0]}: ${s.summary}`).join('\n')}

## INSTRUCTIONS
Generate a 2-3 sentence alert that:
1. States what happened in plain language
2. Notes why it matters (deviation from normal)
3. Suggests immediate relevance (bullish/bearish/neutral signal or operational concern)

Do NOT use headers or bullet points. Write in concise analyst prose.`;
}
```

#### Deep Analysis Prompt

```typescript
// lib/claude/prompts/deep-analysis.ts
export function buildDeepAnalysisPrompt(bundle: SignalContextBundle): string {
  return `You are a senior space economy analyst preparing an intelligence brief for institutional investors.

## PRIMARY SIGNAL
${JSON.stringify(bundle.primarySignal, null, 2)}

## ENTITY PROFILE
${JSON.stringify(bundle.entityProfile, null, 2)}

## ORBITAL CONTEXT
${bundle.orbitalContext ? JSON.stringify(bundle.orbitalContext, null, 2) : 'N/A'}

## MARKET CONTEXT
${bundle.marketContext ? JSON.stringify(bundle.marketContext, null, 2) : 'N/A'}

## RELATED SIGNALS (last 7 days)
${bundle.relatedSignals.map(s => `- [${s.severity}] ${s.anomalyType}: ${s.observedValue}`).join('\n')}

## USER PREFERENCE
Briefing style: ${bundle.userContext.preferredBriefingStyle}

---

Generate a structured intelligence brief with:

1. **SITUATION** (2-3 sentences): What happened and when
2. **ANALYSIS** (2-3 paragraphs): 
   - Technical explanation of the anomaly
   - Historical context and pattern recognition
   - Cross-domain implications (regulatory ↔ physical ↔ market)
3. **ASSESSMENT** (1 paragraph): Investment/strategic implications with confidence level
4. **WATCH ITEMS** (3-5 bullets): Specific follow-up indicators to monitor

Maintain analytical rigor. Avoid speculation without evidence. Cite specific data points.`;
}
```

#### Scheduled Report Prompt

```typescript
// lib/claude/prompts/scheduled-report.ts
export function buildWeeklyReportPrompt(
  watchlistSignals: Signal[],
  portfolioEntities: EntityProfile[]
): string {
  return `You are preparing a weekly intelligence summary for a space economy investor.

## WATCHLIST ACTIVITY (past 7 days)
${watchlistSignals.map(s => `
### ${s.entityName}
- Signal: ${s.anomalyType} (${s.severity})
- Deviation: ${s.zScore.toFixed(1)}σ from baseline
- Raw: ${JSON.stringify(s.rawData)}
`).join('\n')}

## PORTFOLIO ENTITIES
${portfolioEntities.map(e => `
### ${e.name}
- Type: ${e.type}
- Recent signals: ${e.signalHistory.length}
- Status: ${e.satellite?.currentStatus || e.company?.sector}
`).join('\n')}

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
```

---

## Generation Pipeline

### Edge Function: Generate Briefing

```typescript
// supabase/functions/generate-briefing/index.ts
import { createClient } from '@supabase/supabase-js';
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: Deno.env.get('ANTHROPIC_API_KEY')!,
});

Deno.serve(async (req) => {
  const { signalId, briefingType, userId } = await req.json();
  
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );
  
  // 1. Fetch signal
  const { data: signal } = await supabase
    .from('signals')
    .select('*')
    .eq('id', signalId)
    .single();
  
  // 2. Assemble context
  const entityProfile = await assembleEntityProfile(signal.entity_id, signal.entity_type, supabase);
  const relatedSignals = await fetchRelatedSignals(signal, supabase);
  const userContext = await fetchUserContext(userId, signal.entity_id, supabase);
  
  const bundle: SignalContextBundle = {
    primarySignal: signal,
    relatedSignals,
    entityProfile,
    userContext,
  };
  
  // 3. Build prompt based on type
  let prompt: string;
  let model: string;
  let maxTokens: number;
  
  switch (briefingType) {
    case 'flash':
      prompt = buildFlashAlertPrompt(bundle);
      model = 'claude-sonnet-4-20250514';
      maxTokens = 256;
      break;
    case 'deep':
      prompt = buildDeepAnalysisPrompt(bundle);
      model = 'claude-sonnet-4-20250514';
      maxTokens = 2048;
      break;
    default:
      throw new Error(`Unknown briefing type: ${briefingType}`);
  }
  
  // 4. Generate
  const response = await anthropic.messages.create({
    model,
    max_tokens: maxTokens,
    messages: [{ role: 'user', content: prompt }],
  });
  
  const briefingText = response.content[0].type === 'text' 
    ? response.content[0].text 
    : '';
  
  // 5. Store briefing
  const { data: briefing } = await supabase
    .from('briefings')
    .insert({
      signal_id: signalId,
      user_id: userId,
      type: briefingType,
      content: briefingText,
      model_used: model,
      tokens_used: response.usage.output_tokens,
    })
    .select()
    .single();
  
  // 6. Update signal as processed
  await supabase
    .from('signals')
    .update({ processed: true, briefing_id: briefing.id })
    .eq('id', signalId);
  
  return new Response(JSON.stringify({ briefing }), {
    headers: { 'Content-Type': 'application/json' },
  });
});
```

---

## Real-Time Flash Alerts

### Trigger Flow

```
Signal Detected
      │
      ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Check Severity │────▶│  User Subscribed│────▶│ Generate Flash  │
│  (high/critical)│     │  to Entity?     │     │ (Claude API)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┘
                        ▼
              ┌─────────────────┐     ┌─────────────────┐
              │  Store Briefing │────▶│  Push to User   │
              │  in Supabase    │     │  (Realtime +    │
              └─────────────────┘     │   iOS Push)     │
                                      └─────────────────┘
```

### Real-Time Subscription (Client)

```typescript
// hooks/useFlashAlerts.ts
import { useEffect } from 'react';
import { supabase } from '@/lib/supabase';

export function useFlashAlerts(userId: string, onAlert: (briefing: any) => void) {
  useEffect(() => {
    const channel = supabase
      .channel('flash-alerts')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'briefings',
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          if (payload.new.type === 'flash') {
            onAlert(payload.new);
          }
        }
      )
      .subscribe();
    
    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, onAlert]);
}
```

---

## Structured Output (Optional)

For programmatic consumption, request structured JSON:

```typescript
export function buildStructuredAnalysisPrompt(bundle: SignalContextBundle): string {
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
```

---

## Cost Management

### Token Estimation

| Briefing Type | Input Tokens (avg) | Output Tokens (avg) | Cost (Sonnet) |
|---------------|--------------------|--------------------|---------------|
| Flash Alert | ~800 | ~150 | ~$0.003 |
| Signal Summary | ~1,500 | ~400 | ~$0.007 |
| Deep Analysis | ~3,000 | ~1,500 | ~$0.02 |
| Weekly Report | ~5,000 | ~2,000 | ~$0.03 |

### Rate Limiting

```typescript
// lib/claude/rate-limiter.ts
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_URL!,
  token: process.env.UPSTASH_REDIS_TOKEN!,
});

export const briefingLimiter = new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(100, '1 h'), // 100 briefings/hour per user
  analytics: true,
});

export async function checkBriefingLimit(userId: string): Promise<boolean> {
  const { success } = await briefingLimiter.limit(userId);
  return success;
}
```

### Caching Repeated Requests

```typescript
// Cache identical context bundles
const briefingCache = new Map<string, { content: string; expires: number }>();

function getCacheKey(bundle: SignalContextBundle): string {
  return `${bundle.primarySignal.id}-${bundle.primarySignal.updatedAt}`;
}

async function getCachedOrGenerate(bundle: SignalContextBundle): Promise<string> {
  const key = getCacheKey(bundle);
  const cached = briefingCache.get(key);
  
  if (cached && cached.expires > Date.now()) {
    return cached.content;
  }
  
  const content = await generateBriefing(buildFlashAlertPrompt(bundle));
  briefingCache.set(key, { content, expires: Date.now() + 5 * 60 * 1000 }); // 5 min TTL
  
  return content;
}
```

---

## File Structure

| File | Purpose |
|------|---------|
| `lib/claude/client.ts` | Anthropic SDK wrapper |
| `lib/claude/prompts/flash-alert.ts` | Flash alert prompt builder |
| `lib/claude/prompts/deep-analysis.ts` | Deep analysis prompt builder |
| `lib/claude/prompts/scheduled-report.ts` | Weekly/daily report prompts |
| `lib/claude/rate-limiter.ts` | Upstash rate limiting |
| `lib/briefing/context.ts` | Context bundle assembly |
| `lib/briefing/types.ts` | TypeScript interfaces |
| `functions/generate-briefing/` | Edge function for generation |
| `functions/scheduled-reports/` | Cron-triggered report generation |
| `hooks/useFlashAlerts.ts` | Real-time alert subscription |
| `hooks/useBriefing.ts` | On-demand briefing fetching |

---

## Quality Assurance

### Prompt Versioning

Store prompts in database for A/B testing and rollback:

```sql
CREATE TABLE prompt_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  version INT NOT NULL,
  template TEXT NOT NULL,
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  
  UNIQUE(name, version)
);
```

### Human-in-the-Loop (Critical Alerts)

For signals above a severity threshold, queue for human review before distribution:

```typescript
if (signal.severity === 'critical') {
  await supabase.from('briefing_review_queue').insert({
    briefing_id: briefing.id,
    signal_id: signal.id,
    status: 'pending_review',
  });
  // Don't push to users yet
} else {
  await pushBriefingToUsers(briefing);
}
```

---

## Future Enhancements

1. **Multi-modal briefings**: Include charts/visuals generated from Cockpit
2. **Interactive Q&A**: Allow users to ask follow-up questions about a briefing
3. **Confidence scoring**: Use Claude to self-assess analysis confidence
4. **Source citation**: Link claims to specific data points in context bundle
5. **Personalization**: Fine-tune style based on user feedback
