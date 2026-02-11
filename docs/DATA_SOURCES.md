# Data Sources

All external APIs and data integrations for Short Gravity.

---

## Overview

| Source | Purpose | Update Frequency | Cache |
|--------|---------|------------------|-------|
| **Space-Track.org** | Satellite TLE, metadata, maneuvers | Real-time | 6hr TLE, 24hr metadata |
| **Finnhub** | ASTS stock price | 60s polling | None |
| **Alpha Vantage** | Historical OHLCV candles | On-demand | 2hr |
| **SEC EDGAR** | Filings (10-K, 10-Q, 8-K) | Worker polls | Supabase |
| **EPO OPS** | Patent data (US, EP, WO, KR, JP, AU, CA) | On-demand | Supabase |
| **Supabase** | Database (filings, events, patents) | Real-time | N/A |
| **Claude API** | AI summaries for filings | On filing ingest | Stored in DB |

---

## 1. Space-Track.org (Satellites)

Official US Space Force satellite catalog. Provides TLE data for position calculations.

### Setup

1. **Create account**: https://www.space-track.org/auth/createAccount
2. **Verify email**
3. **Add credentials** to `.env.local`:

```bash
SPACE_TRACK_USERNAME=your_username
SPACE_TRACK_PASSWORD=your_password
```

### API Client

**File**: `lib/space-track.ts`

```typescript
import { getLatestTLE, getSatelliteMetadata, getManeuverHistory } from '@/lib/space-track';

// Get TLE for a satellite
const tle = await getLatestTLE('53807'); // BlueWalker 3

// Get metadata (launch date, orbit params)
const metadata = await getSatelliteMetadata('53807');

// Get maneuver history
const maneuvers = await getManeuverHistory('53807');
```

### Hooks

**File**: `lib/hooks/useSatellitePosition.ts`

```typescript
import { useSatellitePosition, useMultipleSatellitePositions } from '@/lib/hooks/useSatellitePosition';

// Track single satellite (updates every 5s)
const { position, isLoading } = useSatellitePosition('53807');
// position: { latitude, longitude, altitude, velocity }

// Track multiple satellites
const positions = useMultipleSatellitePositions(['53807', '61045', '61046']);
// positions['53807'].position.latitude
```

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/satellites/[noradId]` | GET | Full satellite data |
| `/api/satellites/[noradId]/tle` | GET | TLE only |
| `/api/satellites/[noradId]/drag-history` | GET | B* coefficient history |
| `/api/satellites/search?name=X` | GET | Search by name |
| `/api/satellites/batch-tle` | POST | Multiple TLEs |
| `/api/constellation/stats` | GET | ASTS constellation stats |

### ASTS Satellite Catalog

**File**: `lib/asts-satellites.ts`

| Name | NORAD ID | Status |
|------|----------|--------|
| BlueWalker 3 | 53807 | ACTIVE |
| BlueBird 1 | 61045 | ACTIVE |
| BlueBird 2 | 61046 | ACTIVE |
| BlueBird 3 | 61047 | ACTIVE |
| BlueBird 4 | 61048 | ACTIVE |
| BlueBird 5 | 61049 | ACTIVE |
| BlueBird 6 (FM1) | 67232 | COMMISSIONING |

```typescript
import { getActiveSatellites, getConstellationProgress } from '@/lib/asts-satellites';

const satellites = getActiveSatellites();
const progress = getConstellationProgress();
```

### Rate Limits

- **30 requests/minute**
- **300 requests/hour**
- Session expires after 2 hours

Handled by server-side caching:
- TLE: 6 hours
- Metadata: 24 hours
- Maneuvers: 1 hour

### Position Calculation

TLE is fetched once, then **satellite.js** (SGP4) calculates position client-side every 1-5 seconds. No additional API calls needed for real-time updates.

---

## 2. Finnhub (Stock Price)

Real-time ASTS stock quotes.

### Setup

1. **Get API key**: https://finnhub.io/
2. **Add to `.env.local`**:

```bash
FINNHUB_API_KEY=your_api_key
```

### API Client

**File**: `lib/finnhub.ts`

### Hooks

**File**: `lib/hooks/useStockPrice.ts`

```typescript
import { useStockPrice } from '@/lib/hooks/useStockPrice';

const { data, isLoading, error } = useStockPrice('ASTS', 60000); // Poll every 60s
// data: { currentPrice, change, percentChange, high, low, open, previousClose }
```

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/stock/[symbol]` | GET | Current quote |

---

## 3. Alpha Vantage (Historical Candles)

OHLCV data for charts.

### Setup

1. **Get API key**: https://www.alphavantage.co/support/#api-key
2. **Add to `.env.local`**:

```bash
ALPHA_VANTAGE_API_KEY=your_api_key
```

### API Client

**File**: `lib/alpha-vantage.ts`

### Hooks

**File**: `lib/hooks/useStockCandles.ts`

```typescript
import { useStockCandles } from '@/lib/hooks/useStockCandles';

const { data } = useStockCandles('ASTS', 'D', 90); // Daily candles, 90 days
// data.candles: [{ time, open, high, low, close, volume }]
```

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/stock/[symbol]/candles` | GET | Historical OHLCV |

### Cache

2-hour server-side cache (Alpha Vantage has strict rate limits on free tier).

---

## 4. SEC EDGAR (Filings)

SEC filings for ASTS (CIK: 0001780312).

### Setup

No API key needed (public API).

### Python Worker

**File**: `scripts/data-fetchers/filing_worker.py`

Polls SEC EDGAR, generates AI summaries via Claude, stores in Supabase.

```bash
cd scripts/data-fetchers
export $(grep -v '^#' .env | xargs)
python3 filing_worker.py
```

### API Client

**File**: `lib/sec-edgar.ts`

### Hooks

**File**: `lib/hooks/useFilings.ts`

```typescript
import { useFilings } from '@/lib/hooks/useFilings';

const { data, isLoading } = useFilings({ limit: 10, form: '8-K' });
// data.filings: [{ accessionNumber, formType, filedAt, summary }]
```

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/filings` | GET | List filings |
| `/api/filings/[accessionNumber]` | GET | Single filing detail |

---

## 5. Supabase (Database)

PostgreSQL database for persistent data.

### Setup

1. **Create project**: https://supabase.com/
2. **Add to `.env.local`**:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx  # Server-side only
```

### Client

**File**: `lib/supabase.ts`

### Tables

| Table | Purpose |
|-------|---------|
| `filings` | SEC filings with AI summaries |
| `inbox` | Curated events/alerts |
| `high_signal` | Critical signals |
| `news_source` | Aggregated content |

### Migrations

Located in `short-gravity-web/supabase/migrations/`.

---

## 6. Claude API (AI Summaries)

Used by filing worker to generate summaries.

### Setup

Add to `scripts/data-fetchers/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-xxx
```

### Usage

Only used in Python worker, not in web app directly.

---

## 7. EPO OPS (Patents)

European Patent Office Open Patent Services. Covers global patent data including US, EP, WO (PCT), KR, JP, AU, CA.

### Setup

1. **Register**: https://developers.epo.org/
2. **Create app** in Developer Console
3. **Enable "Open Patent Services"** product
4. **Add to `scripts/data-fetchers/.env`**:

```bash
EPO_CONSUMER_KEY=your_consumer_key
EPO_CONSUMER_SECRET=your_consumer_secret
```

### Python Worker

**File**: `scripts/data-fetchers/epo_patent_fetcher.py`

Searches EPO for AST SpaceMobile patents, expands patent families, stores in Supabase.

```bash
cd scripts/data-fetchers
export $(grep -v '^#' .env | xargs)
python3 epo_patent_fetcher.py           # Full fetch
python3 epo_patent_fetcher.py --report  # Report only
python3 epo_patent_fetcher.py --dry-run # Test without saving
```

### Search Queries

Uses EPO CQL syntax:
- `pa=AST and ta=satellite` — AST applicant + satellite in title/abstract
- `in=Avellan and ta=satellite` — Abel Avellan inventor + satellite

### Database

**Table**: `patents`

| Column | Description |
|--------|-------------|
| `patent_number` | e.g., US9973266B1, EP3378176A1 |
| `title` | Invention title |
| `status` | granted/pending |
| `source` | epo_ops, patentsview, etc. |

### Rate Limits

- **20 requests/minute** (free tier)
- Built-in 3.1s delay between requests
- Auto-retry on quota exceeded

### Coverage

**Patents**: 307 records across 29 families

| Jurisdiction | Patents | Source |
|--------------|---------|--------|
| US | 164 | EPO OPS, BigQuery |
| EP | 31 | EPO OPS |
| WO | 21 | EPO OPS |
| KR | 31 | EPO OPS |
| JP | 30 | EPO OPS |
| AU | 18 | EPO OPS |
| CA | 10 | EPO OPS |

**Claims**: 2,482 individual claims (target: ~3,800)

| Source | Claims | Status |
|--------|--------|--------|
| BigQuery (US) | ~2,052 | ✅ Complete |
| EPO fulltext (EP/WO) | ~430 | ✅ Complete |
| JP/KR/AU/CA | ~1,300 | 🔧 Needs local APIs |

### Patent Claims Table

**Table**: `patent_claims`

| Column | Description |
|--------|-------------|
| `patent_number` | e.g., US9973266B1 |
| `claim_number` | Claim sequence (1, 2, 3...) |
| `claim_text` | Full claim text |
| `claim_type` | independent / dependent |
| `depends_on` | Array of referenced claims |

### Additional Fetchers

For claims from international jurisdictions:

| File | Purpose | API Key Needed |
|------|---------|----------------|
| `bigquery_ast_claims.py` | US claims from Google BigQuery | GCP project |
| `epo_claims_fetcher.py` | EP/WO claims from EPO fulltext | EPO credentials |
| `kipris_claims_fetcher.py` | Korean claims | KIPRIS_API_KEY |
| `jplatpat_claims_fetcher.py` | Japanese claims | JPO_API_KEY |
| `ipaustralia_claims_fetcher.py` | Australian claims | IPA credentials |
| `cipo_claims_fetcher.py` | Canadian claims | None (web scrape) |

See `scripts/data-fetchers/INTERNATIONAL_PATENTS_SETUP.md` for API registration details.

---

## 8. Discord/Resend (Notifications)

Optional notifications for waitlist signups.

### Discord Webhook

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx
```

### Resend Email

```bash
RESEND_API_KEY=re_xxx
NOTIFICATION_EMAIL=your@email.com
```

---

## Environment Variables Summary

### Web App (`.env.local`)

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# APIs
FINNHUB_API_KEY=
ALPHA_VANTAGE_API_KEY=
SPACE_TRACK_USERNAME=
SPACE_TRACK_PASSWORD=

# Optional: Notifications
DISCORD_WEBHOOK_URL=
RESEND_API_KEY=
NOTIFICATION_EMAIL=
ADMIN_SECRET_KEY=

# Vercel (production)
QSTASH_CURRENT_SIGNING_KEY=
QSTASH_NEXT_SIGNING_KEY=
```

### Python Workers (`scripts/data-fetchers/.env`)

```bash
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=

# Patent APIs
EPO_CONSUMER_KEY=
EPO_CONSUMER_SECRET=
PATENTSVIEW_API_KEY=
```

---

## Troubleshooting

### Space-Track 401 Error

- Verify credentials at https://www.space-track.org/auth/login
- Check for typos in username/password
- Ensure account is verified

### Rate Limit Exceeded

- Wait 60 seconds
- Check that caching is working (server logs show "cache hit")
- Reduce polling frequency

### Missing Environment Variable

- Restart dev server after adding to `.env.local`
- Ensure no spaces around `=`
- Check variable name matches exactly

---

## Adding New Data Sources

1. Create API client in `lib/[source].ts`
2. Create hook in `lib/hooks/use[Source].ts`
3. Create API route in `app/api/[source]/route.ts`
4. Add env vars to `.env.example`
5. Document here
