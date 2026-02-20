# Data Model Architecture

**Layer:** PostgreSQL (Supabase)  
**Version:** 1.0

---

## Overview

The data model supports three core domains: entities (satellites, companies), signals (anomalies), and user data (watchlists, briefings). Designed for real-time subscriptions, row-level security, and time-series queries.

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA MODEL                                      │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
  │   PROFILES   │         │   ENTITIES   │         │  SATELLITES  │
  │   (users)    │         │   (core)     │         │  (extends)   │
  └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
         │                        │                        │
         │ 1:N                    │ 1:1                    │
         │                        ▼                        │
         │                 ┌──────────────┐                │
         │                 │  COMPANIES   │◀───────────────┘
         │                 │  (extends)   │
         │                 └──────────────┘
         │
         │                        │
         │                        │ 1:N
         │                        ▼
         │                 ┌──────────────┐
         │                 │   SIGNALS    │
         │                 │  (anomalies) │
         │                 └──────┬───────┘
         │                        │
         │                        │ 1:1
         │                        ▼
         │                 ┌──────────────┐
         └────────────────▶│  BRIEFINGS   │
               1:N         │  (AI output) │
                           └──────────────┘
         │
         │ N:M (via junction)
         ▼
  ┌──────────────┐
  │  WATCHLISTS  │
  │  (user→entity)│
  └──────────────┘
```

---

## Core Tables

### profiles (Users)

```sql
-- Extends Supabase auth.users
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  avatar_url TEXT,
  
  -- Subscription tier
  tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
  tier_expires_at TIMESTAMPTZ,
  
  -- Preferences
  briefing_style TEXT DEFAULT 'balanced' CHECK (briefing_style IN ('technical', 'executive', 'balanced')),
  push_enabled BOOLEAN DEFAULT true,
  email_digest TEXT DEFAULT 'daily' CHECK (email_digest IN ('none', 'daily', 'weekly')),
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Trigger to create profile on user signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

### entities (Core Entity Registry)

```sql
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  type TEXT NOT NULL CHECK (type IN ('satellite', 'company', 'constellation', 'ground_station')),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL, -- URL-friendly identifier
  description TEXT,
  
  -- External IDs
  norad_id TEXT,          -- For satellites
  ticker TEXT,            -- For companies
  sec_cik TEXT,           -- SEC Central Index Key
  
  -- Status
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'decommissioned')),
  
  -- Metadata
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_norad_id ON entities(norad_id) WHERE norad_id IS NOT NULL;
CREATE INDEX idx_entities_ticker ON entities(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX idx_entities_slug ON entities(slug);
```

### satellites (Satellite Extension)

```sql
CREATE TABLE satellites (
  id UUID PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
  norad_id TEXT UNIQUE NOT NULL,
  
  -- Constellation membership
  constellation_id UUID REFERENCES entities(id),
  operator_id UUID REFERENCES entities(id), -- Company that operates
  
  -- Orbital parameters (from TLE)
  orbit_type TEXT CHECK (orbit_type IN ('LEO', 'MEO', 'GEO', 'HEO', 'SSO', 'MOLNIYA')),
  inclination_deg DECIMAL(6,3),
  apogee_km DECIMAL(10,2),
  perigee_km DECIMAL(10,2),
  period_min DECIMAL(8,2),
  
  -- Mission info
  purpose TEXT,
  launch_date DATE,
  launch_vehicle TEXT,
  launch_site TEXT,
  
  -- Current TLE (most recent)
  tle_line1 TEXT,
  tle_line2 TEXT,
  tle_epoch TIMESTAMPTZ,
  
  -- Status
  operational_status TEXT DEFAULT 'unknown' 
    CHECK (operational_status IN ('operational', 'partially_operational', 'non_operational', 'unknown', 'decayed')),
  
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_satellites_constellation ON satellites(constellation_id);
CREATE INDEX idx_satellites_operator ON satellites(operator_id);
CREATE INDEX idx_satellites_orbit_type ON satellites(orbit_type);
```

### companies (Company Extension)

```sql
CREATE TABLE companies (
  id UUID PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
  
  -- Identifiers
  ticker TEXT,
  exchange TEXT,
  sec_cik TEXT,
  
  -- Profile
  sector TEXT,
  industry TEXT,
  founded_year INT,
  headquarters TEXT,
  website TEXT,
  
  -- Financials (cached, updated periodically)
  market_cap BIGINT,
  employees INT,
  
  -- Space-specific
  satellite_count INT DEFAULT 0,
  constellation_ids UUID[] DEFAULT '{}',
  
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_companies_ticker ON companies(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX idx_companies_sector ON companies(sector);
```

### signals (Anomaly Events)

```sql
CREATE TABLE signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Classification
  anomaly_type TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  
  -- Entity reference
  entity_id UUID NOT NULL REFERENCES entities(id),
  entity_type TEXT NOT NULL,
  entity_name TEXT NOT NULL, -- Denormalized for query speed
  
  -- Anomaly metrics
  metric_type TEXT NOT NULL,
  observed_value DECIMAL,
  baseline_value DECIMAL,
  z_score DECIMAL(6,3),
  
  -- Raw data capture
  raw_data JSONB DEFAULT '{}',
  source TEXT NOT NULL, -- 'space-track', 'edgar', 'market', etc.
  
  -- Relationships
  related_signal_ids UUID[] DEFAULT '{}',
  
  -- Processing state
  processed BOOLEAN DEFAULT false,
  briefing_id UUID REFERENCES briefings(id),
  
  -- Timestamps
  detected_at TIMESTAMPTZ DEFAULT now(),
  event_time TIMESTAMPTZ, -- When the anomaly actually occurred
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_signals_entity ON signals(entity_id);
CREATE INDEX idx_signals_severity ON signals(severity);
CREATE INDEX idx_signals_type ON signals(anomaly_type);
CREATE INDEX idx_signals_detected_at ON signals(detected_at DESC);
CREATE INDEX idx_signals_unprocessed ON signals(processed) WHERE processed = false;

-- Partitioning by month for performance
-- CREATE TABLE signals_2026_01 PARTITION OF signals FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### baselines (Statistical Baselines)

```sql
CREATE TABLE baselines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Reference
  entity_id UUID NOT NULL REFERENCES entities(id),
  metric_type TEXT NOT NULL,
  
  -- Statistics
  mean DECIMAL NOT NULL,
  std_dev DECIMAL NOT NULL,
  median DECIMAL,
  percentile_95 DECIMAL,
  
  -- Window
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  sample_count INT NOT NULL,
  
  -- Threshold config
  anomaly_threshold_sigma DECIMAL DEFAULT 2.0,
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  
  UNIQUE(entity_id, metric_type)
);

CREATE INDEX idx_baselines_entity_metric ON baselines(entity_id, metric_type);
```

### briefings (AI-Generated Content)

```sql
CREATE TABLE briefings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- References
  user_id UUID NOT NULL REFERENCES profiles(id),
  signal_id UUID REFERENCES signals(id),
  
  -- Content
  type TEXT NOT NULL CHECK (type IN ('flash', 'summary', 'deep', 'scheduled')),
  title TEXT,
  content TEXT NOT NULL,
  structured_content JSONB, -- Optional structured version
  
  -- AI metadata
  model_used TEXT NOT NULL,
  tokens_input INT,
  tokens_output INT,
  prompt_version INT,
  
  -- State
  read BOOLEAN DEFAULT false,
  archived BOOLEAN DEFAULT false,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_briefings_user ON briefings(user_id);
CREATE INDEX idx_briefings_signal ON briefings(signal_id);
CREATE INDEX idx_briefings_created_at ON briefings(created_at DESC);
CREATE INDEX idx_briefings_unread ON briefings(user_id, read) WHERE read = false;
```

### watchlists (User→Entity Subscription)

```sql
CREATE TABLE watchlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  
  -- Configuration
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low')),
  
  -- Alert preferences (overrides user defaults)
  alert_on_severity TEXT[] DEFAULT '{high,critical}',
  alert_types TEXT[], -- Null = all types
  
  -- Custom thresholds
  custom_thresholds JSONB DEFAULT '{}',
  
  -- Notes
  notes TEXT,
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT now(),
  
  UNIQUE(user_id, entity_id)
);

CREATE INDEX idx_watchlists_user ON watchlists(user_id);
CREATE INDEX idx_watchlists_entity ON watchlists(entity_id);
```

### tle_history (TLE Archive)

```sql
CREATE TABLE tle_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  satellite_id UUID NOT NULL REFERENCES satellites(id),
  norad_id TEXT NOT NULL,
  
  -- TLE data
  tle_line1 TEXT NOT NULL,
  tle_line2 TEXT NOT NULL,
  epoch TIMESTAMPTZ NOT NULL,
  
  -- Derived values (for querying)
  mean_motion DECIMAL(12,8),
  eccentricity DECIMAL(10,8),
  inclination DECIMAL(8,4),
  
  -- Source
  source TEXT DEFAULT 'space-track',
  
  -- Timestamp
  fetched_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tle_history_satellite ON tle_history(satellite_id);
CREATE INDEX idx_tle_history_epoch ON tle_history(epoch DESC);
CREATE INDEX idx_tle_history_norad_epoch ON tle_history(norad_id, epoch DESC);

-- Keep only 90 days of history
-- CREATE POLICY tle_retention ON tle_history FOR DELETE USING (fetched_at < now() - INTERVAL '90 days');
```

### metric_history (Time-Series Metrics)

```sql
CREATE TABLE metric_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES entities(id),
  metric_type TEXT NOT NULL,
  value DECIMAL NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_metric_history_entity_type ON metric_history(entity_id, metric_type);
CREATE INDEX idx_metric_history_timestamp ON metric_history(timestamp DESC);

-- Hypertable for TimescaleDB (if enabled)
-- SELECT create_hypertable('metric_history', 'timestamp');
```

---

## Row-Level Security (RLS)

### Enable RLS on All Tables

```sql
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE briefings ENABLE ROW LEVEL SECURITY;
-- entities, signals, satellites, companies are public read
```

### Policies

```sql
-- Profiles: Users can only access their own profile
CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);

-- Watchlists: Users can only access their own watchlists
CREATE POLICY "Users can view own watchlists"
  ON watchlists FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own watchlists"
  ON watchlists FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlists"
  ON watchlists FOR DELETE
  USING (auth.uid() = user_id);

-- Briefings: Users can only access their own briefings
CREATE POLICY "Users can view own briefings"
  ON briefings FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert briefings"
  ON briefings FOR INSERT
  WITH CHECK (true); -- Edge functions use service role

-- Entities: Public read access
CREATE POLICY "Public can view entities"
  ON entities FOR SELECT
  USING (true);

-- Signals: Public read access
CREATE POLICY "Public can view signals"
  ON signals FOR SELECT
  USING (true);
```

---

## Views

### User Dashboard View

```sql
CREATE VIEW user_dashboard AS
SELECT 
  w.user_id,
  e.id AS entity_id,
  e.name AS entity_name,
  e.type AS entity_type,
  w.priority,
  (
    SELECT COUNT(*)
    FROM signals s
    WHERE s.entity_id = e.id
      AND s.detected_at > now() - INTERVAL '24 hours'
  ) AS signals_24h,
  (
    SELECT s.anomaly_type
    FROM signals s
    WHERE s.entity_id = e.id
    ORDER BY s.detected_at DESC
    LIMIT 1
  ) AS latest_signal_type
FROM watchlists w
JOIN entities e ON e.id = w.entity_id;
```

### Signal Feed View

```sql
CREATE VIEW signal_feed AS
SELECT 
  s.*,
  e.name AS entity_display_name,
  e.slug AS entity_slug,
  CASE 
    WHEN s.severity = 'critical' THEN 1
    WHEN s.severity = 'high' THEN 2
    WHEN s.severity = 'medium' THEN 3
    ELSE 4
  END AS severity_rank
FROM signals s
JOIN entities e ON e.id = s.entity_id
WHERE s.detected_at > now() - INTERVAL '7 days'
ORDER BY s.detected_at DESC;
```

---

## Real-Time Subscriptions

### Enable Real-Time for Key Tables

```sql
-- In Supabase Dashboard or via SQL
ALTER PUBLICATION supabase_realtime ADD TABLE signals;
ALTER PUBLICATION supabase_realtime ADD TABLE briefings;
```

### Client Subscription Example

```typescript
// Subscribe to new signals for watchlist entities
const channel = supabase
  .channel('watchlist-signals')
  .on(
    'postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'signals',
      filter: `entity_id=in.(${watchlistEntityIds.join(',')})`,
    },
    (payload) => handleNewSignal(payload.new)
  )
  .subscribe();
```

---

## Indexes Summary

| Table | Index | Purpose |
|-------|-------|---------|
| `entities` | `idx_entities_type` | Filter by entity type |
| `entities` | `idx_entities_slug` | URL lookups |
| `satellites` | `idx_satellites_constellation` | Constellation grouping |
| `signals` | `idx_signals_detected_at` | Time-series queries |
| `signals` | `idx_signals_unprocessed` | Processing queue |
| `briefings` | `idx_briefings_unread` | Unread count badges |
| `tle_history` | `idx_tle_history_norad_epoch` | TLE lookups |
| `metric_history` | `idx_metric_history_timestamp` | Time-series queries |

---

## Migration Files

| File | Description |
|------|-------------|
| `001_initial_schema.sql` | Core tables and indexes |
| `002_add_rls_policies.sql` | Row-level security |
| `003_create_views.sql` | Dashboard and feed views |
| `004_add_realtime.sql` | Enable real-time subscriptions |
| `005_seed_entities.sql` | Initial satellite/company data |

---

## Seed Data Sources

| Entity Type | Source | Update Frequency |
|-------------|--------|------------------|
| Satellites | CelesTrak SATCAT | Weekly |
| Companies | Manual curation | As needed |
| TLEs | Space-Track.org | Every 2 hours |
| Market data | Provider API | Real-time/delayed |
