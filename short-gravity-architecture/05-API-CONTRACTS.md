# API Contracts

**Layer:** Supabase Edge Functions + Client SDK  
**Version:** 1.0

---

## Overview

Short Gravity exposes APIs via:
1. **Supabase Client SDK** — Direct database access with RLS
2. **Edge Functions** — Custom logic, AI integration, external APIs
3. **Real-Time** — WebSocket subscriptions for live updates

---

## Base URLs

| Environment | Supabase URL | Edge Functions |
|-------------|--------------|----------------|
| Development | `http://localhost:54321` | `http://localhost:54321/functions/v1` |
| Production | `https://<project>.supabase.co` | `https://<project>.supabase.co/functions/v1` |

---

## Authentication

All requests require a JWT in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Obtain tokens via Supabase Auth (email/password, OAuth, magic link).

---

## Entities API

### List Entities

```typescript
const { data, error } = await supabase
  .from('entities')
  .select(`*, satellites(*), companies(*)`)
  .eq('type', 'satellite')
  .order('name')
  .range(0, 49);
```

### Get Entity by Slug

```typescript
const { data, error } = await supabase
  .from('entities')
  .select(`*, satellites(*), companies(*), signals(*)`)
  .eq('slug', 'starlink-1234')
  .single();
```

### Search Entities

**Edge Function:** `POST /functions/v1/search-entities`

```typescript
// Request
{ query: string; types?: string[]; limit?: number; }

// Response
{ results: Entity[]; total: number; }
```

---

## Signals API

### List Signals

```typescript
const { data, error } = await supabase
  .from('signals')
  .select('*')
  .in('entity_id', watchlistEntityIds)
  .gte('detected_at', sevenDaysAgo)
  .order('detected_at', { ascending: false })
  .limit(50);
```

### Subscribe to Real-Time Signals

```typescript
const channel = supabase
  .channel('signals-feed')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'signals',
  }, (payload) => handleNewSignal(payload.new))
  .subscribe();
```

---

## Briefings API

### Generate Briefing

**Edge Function:** `POST /functions/v1/generate-briefing`

```typescript
// Request
{ signal_id: string; briefing_type: 'flash' | 'summary' | 'deep'; }

// Response
{ briefing: Briefing; }
```

### List User Briefings

```typescript
const { data, error } = await supabase
  .from('briefings')
  .select('*')
  .eq('user_id', userId)
  .order('created_at', { ascending: false });
```

### Mark as Read

```typescript
await supabase
  .from('briefings')
  .update({ read: true })
  .eq('id', briefingId);
```

---

## Watchlist API

### Get User Watchlist

```typescript
const { data, error } = await supabase
  .from('watchlists')
  .select(`*, entities(*, satellites(*), companies(*))`)
  .eq('user_id', userId);
```

### Add to Watchlist

```typescript
await supabase
  .from('watchlists')
  .insert({
    user_id: userId,
    entity_id: entityId,
    priority: 'high',
    alert_on_severity: ['high', 'critical'],
  });
```

### Remove from Watchlist

```typescript
await supabase.from('watchlists').delete().eq('id', watchlistItemId);
```

---

## Orbital Data API

### Get Satellite Position

**Edge Function:** `GET /functions/v1/satellite-position`

```typescript
// Query: ?satellite_id=uuid&timestamp=ISO8601

// Response
{
  satellite_id: string;
  timestamp: string;
  eci: { x: number; y: number; z: number }; // km
  velocity: { x: number; y: number; z: number }; // km/s
  geodetic: { latitude: number; longitude: number; altitude: number };
  tle_epoch: string;
}
```

### Get Constellation Positions

**Edge Function:** `POST /functions/v1/constellation-positions`

```typescript
// Request
{ constellation_id?: string; satellite_ids?: string[]; timestamp?: string; }

// Response
{ timestamp: string; positions: PositionResponse[]; }
```

### Get Orbit Path

**Edge Function:** `GET /functions/v1/orbit-path`

```typescript
// Query: ?satellite_id=uuid&duration_minutes=90&steps=180

// Response
{
  satellite_id: string;
  path: Array<{
    timestamp: string;
    geodetic: { latitude: number; longitude: number; altitude: number };
  }>;
}
```

### Calculate Coverage

**Edge Function:** `POST /functions/v1/coverage`

```typescript
// Request
{ satellite_id: string; min_elevation_deg?: number; timestamp?: string; }

// Response
{
  footprint_radius_km: number;
  center: { latitude: number; longitude: number };
  footprint_geojson: GeoJSON.Polygon;
}
```

### Check Line of Sight

**Edge Function:** `POST /functions/v1/line-of-sight`

```typescript
// Request
{
  satellite_id: string;
  ground_location: { latitude: number; longitude: number; altitude_m?: number };
  timestamp?: string;
}

// Response
{
  visible: boolean;
  elevation_deg: number;
  azimuth_deg: number;
  range_km: number;
  next_pass?: { aos: string; los: string; max_elevation_deg: number };
}
```

---

## Push Notifications (iOS)

**Edge Function:** `POST /functions/v1/register-push-token`

```typescript
// Request
{ token: string; platform: 'ios' | 'android'; }

// Response
{ success: boolean; }
```

---

## Error Responses

```typescript
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
```

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH_REQUIRED` | 401 | Missing/invalid JWT |
| `FORBIDDEN` | 403 | Permission denied |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request |
| `RATE_LIMITED` | 429 | Too many requests |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| SDK queries | 1000/min | per user |
| Edge Functions | 100/min | per user |
| Briefing generation | 50/hr | per user |
| Orbital calculations | 200/min | per user |

---

## TypeScript Types

```typescript
export interface Entity {
  id: string;
  type: 'satellite' | 'company' | 'constellation' | 'ground_station';
  name: string;
  slug: string;
  description: string | null;
  norad_id: string | null;
  ticker: string | null;
  status: 'active' | 'inactive' | 'decommissioned';
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Signal {
  id: string;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  entity_id: string;
  entity_type: string;
  entity_name: string;
  metric_type: string;
  observed_value: number | null;
  baseline_value: number | null;
  z_score: number | null;
  raw_data: Record<string, unknown>;
  source: string;
  processed: boolean;
  briefing_id: string | null;
  detected_at: string;
  created_at: string;
}

export interface Briefing {
  id: string;
  user_id: string;
  signal_id: string | null;
  type: 'flash' | 'summary' | 'deep' | 'scheduled';
  title: string | null;
  content: string;
  model_used: string;
  read: boolean;
  created_at: string;
}

export interface WatchlistItem {
  id: string;
  user_id: string;
  entity_id: string;
  priority: 'high' | 'medium' | 'low';
  alert_on_severity: string[];
  notes: string | null;
  created_at: string;
}

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  tier: 'free' | 'pro' | 'enterprise';
  briefing_style: 'technical' | 'executive' | 'balanced';
  push_enabled: boolean;
  email_digest: 'none' | 'daily' | 'weekly';
}
```

---

## File Structure

| File | Purpose |
|------|---------|
| `lib/api/entities.ts` | Entity CRUD |
| `lib/api/signals.ts` | Signal queries |
| `lib/api/briefings.ts` | Briefing operations |
| `lib/api/watchlist.ts` | Watchlist management |
| `lib/api/orbital.ts` | Position calculations |
| `lib/api/types.ts` | TypeScript interfaces |
| `functions/*/` | Edge function implementations |
