# Signal Engine Architecture

**Component:** The Signal Engine  
**Function:** Autonomous Anomaly Detection  
**Version:** 1.0

---

## Overview

The Signal Engine is a system of listeners that continuously monitors specific data streams to establish baselines and detect deviations. It transforms raw data chaos into actionable signals.

---

## Data Streams

### 1. Regulatory Stream

**Sources:**
- FCC filings (spectrum allocations, license modifications)
- FAA notifications (launch windows, airspace closures)
- ITU filings (international frequency coordination)
- SEC/EDGAR (space company filings, 8-K events)
- NOAA (environmental permits)

**Ingestion Method:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  RSS/Atom    │────▶│  Scheduled   │────▶│  Normalize   │
│  Feeds       │     │  Poller      │     │  & Store     │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  SEC EDGAR   │────▶│  API Client  │────▶│  Parse &     │
│  API         │     │  (Rate Ltd)  │     │  Extract     │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Polling Frequency:** 15 minutes (regulatory data updates slowly)

---

### 2. Physical Stream

**Sources:**
- Space-Track.org (authoritative TLE data)
- CelesTrak (supplementary TLEs)
- NORAD catalog updates
- Conjunction warnings (18th Space Defense Squadron)

**Ingestion Method:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Space-Track │────▶│  Auth'd API  │────▶│  TLE Parser  │
│  REST API    │     │  Client      │     │  (satellite.js)
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  Propagate & │
                                          │  Store State │
                                          └──────────────┘
```

**Polling Frequency:** 
- TLE updates: Every 2 hours (orbital elements update ~2x daily)
- Conjunction warnings: Real-time webhook or 30-minute poll

---

### 3. Market Stream

**Sources:**
- Stock prices (relevant tickers: ASTS, RKLB, SPCE, etc.)
- Options flow (unusual activity detection)
- News sentiment (space-focused news APIs)
- Analyst ratings changes

**Ingestion Method:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Market Data │────▶│  WebSocket   │────▶│  Real-time   │
│  Provider    │     │  Client      │     │  Buffer      │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  News APIs   │────▶│  Polling +   │────▶│  Sentiment   │
│              │     │  Webhooks    │     │  Classifier  │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Polling Frequency:**
- Market data: Real-time during market hours, 15-min delayed otherwise
- News: 5-minute polling

---

## Baseline System

The baseline establishes "normal" for each monitored entity, enabling anomaly detection.

### Baseline Types

| Type | Description | Window | Update Frequency |
|------|-------------|--------|------------------|
| **Orbital Baseline** | Expected position/velocity variance | 30 days | Daily |
| **Filing Baseline** | Normal filing frequency per entity | 90 days | Weekly |
| **Market Baseline** | Price/volume statistical norms | 20 days | Daily |
| **News Baseline** | Normal mention frequency | 14 days | Daily |

### Baseline Calculation

```typescript
interface Baseline {
  entityId: string;
  entityType: 'satellite' | 'company' | 'ticker';
  metricType: string;
  
  // Statistical measures
  mean: number;
  stdDev: number;
  median: number;
  percentile95: number;
  
  // Time series
  windowStart: Date;
  windowEnd: Date;
  sampleCount: number;
  
  // Thresholds (configurable)
  anomalyThresholdSigma: number; // default: 2.0
  
  updatedAt: Date;
}
```

### Baseline Edge Function

```typescript
// supabase/functions/update-baselines/index.ts
import { createClient } from '@supabase/supabase-js';

Deno.serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );
  
  // Fetch historical data for window
  const { data: history } = await supabase
    .from('metric_history')
    .select('*')
    .gte('timestamp', windowStart)
    .lte('timestamp', windowEnd);
  
  // Calculate statistics
  const baseline = calculateStatistics(history);
  
  // Upsert baseline
  await supabase
    .from('baselines')
    .upsert(baseline, { onConflict: 'entity_id,metric_type' });
  
  return new Response(JSON.stringify({ success: true }));
});
```

---

## Anomaly Detection

### Detection Algorithm

For each incoming data point:

1. **Fetch relevant baseline** for entity + metric type
2. **Calculate z-score**: `z = (observed - mean) / stdDev`
3. **Check threshold**: If `|z| > anomalyThresholdSigma`, flag as anomaly
4. **Context enrichment**: Attach related data points
5. **Push to signal queue**

### Anomaly Types

| Code | Type | Trigger | Severity |
|------|------|---------|----------|
| `ORB-DEV` | Orbital Deviation | Position > 2σ from predicted | Medium |
| `ORB-MAN` | Maneuver Detected | Sudden velocity change | High |
| `REG-UNU` | Unusual Filing | Filing type outside normal pattern | Medium |
| `REG-UPD` | License Update | Modification to existing license | High |
| `MKT-VOL` | Volume Spike | Volume > 3σ from baseline | Medium |
| `MKT-PRC` | Price Movement | Price change > 2σ intraday | High |
| `MKT-OPT` | Options Activity | Unusual options flow detected | High |
| `NEWS-SPIKE` | News Surge | Mention frequency > 3σ | Medium |

### Signal Schema

```typescript
interface Signal {
  id: string;
  createdAt: Date;
  
  // Classification
  anomalyType: AnomalyType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  
  // Entity reference
  entityId: string;
  entityType: 'satellite' | 'company' | 'ticker' | 'filing';
  entityName: string;
  
  // Anomaly details
  metricType: string;
  observedValue: number;
  baselineValue: number;
  zScore: number;
  
  // Context
  rawData: Record<string, unknown>;
  relatedSignals: string[]; // IDs of correlated signals
  
  // Processing state
  processed: boolean;
  briefingId: string | null; // Link to generated briefing
}
```

---

## Signal Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SIGNAL PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────┘

  Data Sources          Ingestion           Detection           Output
  ────────────          ─────────           ─────────           ──────

┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│ Regulatory  │────▶│              │     │              │     │          │
└─────────────┘     │              │     │              │     │  Signal  │
                    │   Ingest &   │────▶│   Anomaly    │────▶│  Queue   │
┌─────────────┐     │   Normalize  │     │   Detector   │     │          │
│ Physical    │────▶│              │     │              │     │          │
└─────────────┘     │              │     │              │     └────┬─────┘
                    │              │     │              │          │
┌─────────────┐     │              │     │              │          │
│ Market      │────▶│              │     │              │          │
└─────────────┘     └──────────────┘     └──────────────┘          │
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    │
                    ▼
              ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
              │   Realtime   │     │    Push      │     │   Briefing   │
              │   Broadcast  │     │   Notifier   │     │   Trigger    │
              │   (Supabase) │     │   (iOS)      │     │   (Claude)   │
              └──────────────┘     └──────────────┘     └──────────────┘
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `functions/ingest-regulatory/` | Regulatory data polling and parsing |
| `functions/ingest-physical/` | TLE fetching and propagation |
| `functions/ingest-market/` | Market data WebSocket client |
| `functions/update-baselines/` | Scheduled baseline recalculation |
| `functions/detect-anomalies/` | Core anomaly detection logic |
| `functions/push-signal/` | Signal queue and notification dispatch |
| `lib/signal-types.ts` | TypeScript types for signals |
| `lib/baseline-calc.ts` | Statistical calculation utilities |

---

## Configuration

```typescript
// config/signal-engine.ts
export const signalEngineConfig = {
  // Polling intervals (ms)
  polling: {
    regulatory: 15 * 60 * 1000,  // 15 min
    physical: 2 * 60 * 60 * 1000, // 2 hours
    market: 5 * 60 * 1000,        // 5 min (news)
  },
  
  // Baseline windows (days)
  baselineWindows: {
    orbital: 30,
    filing: 90,
    market: 20,
    news: 14,
  },
  
  // Default anomaly thresholds (σ)
  thresholds: {
    default: 2.0,
    orbital: 2.0,
    market: 2.5,
    news: 3.0,
  },
  
  // Rate limits
  rateLimits: {
    spaceTrack: 20,  // requests per minute
    edgar: 10,
    marketData: 100,
  },
};
```

---

## External API Credentials Required

| Service | Credential Type | Notes |
|---------|-----------------|-------|
| Space-Track.org | Username/Password | Free registration required |
| SEC EDGAR | User-Agent header | Rate limit: 10 req/sec |
| Market Data | API Key | Provider-specific (Alpha Vantage, Polygon, etc.) |
| News API | API Key | NewsAPI, Newsdata.io, or similar |

Store all credentials in Supabase Vault or environment variables. Never commit to repository.

---

## Scaling Considerations

- **Horizontal scaling**: Edge Functions auto-scale per request
- **Data volume**: Expect ~10K TLE updates/day, ~1K filings/day, ~100K market ticks/day
- **Storage**: Partition `metric_history` by month for query performance
- **Caching**: Cache baselines in-memory for hot paths (1-hour TTL)
