-- ============================================================================
-- SHORT GRAVITY: TLE Pipeline Tables
-- Run this in Supabase SQL Editor
-- ============================================================================

-- Satellites table: Current state of each tracked satellite
CREATE TABLE IF NOT EXISTS satellites (
  norad_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,

  -- Current TLE (most recent)
  tle_line0 TEXT,                      -- Name line
  tle_line1 TEXT,                      -- TLE line 1
  tle_line2 TEXT,                      -- TLE line 2
  tle_epoch TIMESTAMPTZ,               -- When TLE was measured

  -- Orbital parameters (extracted for fast queries)
  bstar DECIMAL(20,14),                -- Drag coefficient (THE ALPHA)
  mean_motion DECIMAL(13,8),           -- Revolutions per day
  mean_motion_dot DECIMAL(10,8),       -- First derivative (decay rate)
  mean_motion_ddot DECIMAL(22,13),     -- Second derivative
  inclination DECIMAL(8,4),            -- Orbital tilt (degrees)
  eccentricity DECIMAL(13,8),          -- Orbit shape (0 = circular)
  ra_of_asc_node DECIMAL(8,4),         -- RAAN (degrees)
  arg_of_pericenter DECIMAL(8,4),      -- Argument of perigee
  mean_anomaly DECIMAL(8,4),           -- Mean anomaly
  semimajor_axis DECIMAL(12,3),        -- Orbit size (km)
  period_minutes DECIMAL(12,3),        -- Orbital period
  apoapsis_km DECIMAL(12,3),           -- Apogee altitude
  periapsis_km DECIMAL(12,3),          -- Perigee altitude
  rev_at_epoch INT,                    -- Total revolutions

  -- Metadata
  object_type TEXT,                    -- PAYLOAD, ROCKET BODY, DEBRIS
  rcs_size TEXT,                       -- Radar cross-section (SMALL/MEDIUM/LARGE)
  country_code TEXT,                   -- US for ASTS
  launch_date DATE,
  decay_date DATE,                     -- NULL if still orbiting

  -- Full raw response for future analysis
  raw_gp JSONB,

  -- Tracking
  constellation TEXT DEFAULT 'ASTS',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- TLE history: Every TLE ever recorded (for trend analysis)
CREATE TABLE IF NOT EXISTS tle_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  norad_id TEXT NOT NULL,
  epoch TIMESTAMPTZ NOT NULL,

  -- TLE lines
  tle_line0 TEXT,
  tle_line1 TEXT NOT NULL,
  tle_line2 TEXT NOT NULL,

  -- Key orbital parameters (extracted for fast queries)
  bstar DECIMAL(20,14),
  mean_motion DECIMAL(13,8),
  mean_motion_dot DECIMAL(10,8),
  apoapsis_km DECIMAL(12,3),
  periapsis_km DECIMAL(12,3),
  eccentricity DECIMAL(13,8),
  inclination DECIMAL(8,4),
  semimajor_axis DECIMAL(12,3),
  period_minutes DECIMAL(12,3),
  rev_at_epoch INT,

  -- Full raw response
  raw_gp JSONB NOT NULL,

  -- Tracking
  fetched_at TIMESTAMPTZ DEFAULT now(),

  -- Prevent duplicate TLEs (same satellite, same epoch)
  UNIQUE(norad_id, epoch)
);

-- Conjunctions: Close approach warnings (collision risk)
CREATE TABLE IF NOT EXISTS conjunctions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cdm_id INT UNIQUE,                   -- Space-Track CDM ID

  -- Primary object (our satellite)
  sat1_norad_id TEXT,
  sat1_name TEXT,
  sat1_object_type TEXT,

  -- Secondary object (debris/other satellite)
  sat2_norad_id TEXT,
  sat2_name TEXT,
  sat2_object_type TEXT,

  -- Conjunction details
  tca TIMESTAMPTZ,                     -- Time of Closest Approach
  min_range_km DECIMAL(12,6),          -- Miss distance in kilometers
  collision_probability DECIMAL(30,25), -- PC value (can be very small)

  -- Risk assessment
  emergency_reportable BOOLEAN DEFAULT false,

  -- Full raw response
  raw_cdm JSONB,

  -- Tracking
  created_at TIMESTAMPTZ DEFAULT now(),
  fetched_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Satellites: Fast lookup by constellation
CREATE INDEX IF NOT EXISTS idx_satellites_constellation ON satellites(constellation);

-- TLE History: Fast time-series queries
CREATE INDEX IF NOT EXISTS idx_tle_history_norad ON tle_history(norad_id);
CREATE INDEX IF NOT EXISTS idx_tle_history_epoch ON tle_history(epoch DESC);
CREATE INDEX IF NOT EXISTS idx_tle_history_norad_epoch ON tle_history(norad_id, epoch DESC);

-- Conjunctions: Find events for our satellites
CREATE INDEX IF NOT EXISTS idx_conjunctions_sat1 ON conjunctions(sat1_norad_id);
CREATE INDEX IF NOT EXISTS idx_conjunctions_sat2 ON conjunctions(sat2_norad_id);
CREATE INDEX IF NOT EXISTS idx_conjunctions_tca ON conjunctions(tca DESC);

-- ============================================================================
-- SEED DATA: ASTS Constellation
-- ============================================================================

INSERT INTO satellites (norad_id, name, constellation, launch_date) VALUES
  ('67232', 'BLUEWALKER 3-FM1', 'ASTS', '2025-01-14'),
  ('61046', 'BLUEBIRD 5', 'ASTS', '2024-09-12'),
  ('61049', 'BLUEBIRD 4', 'ASTS', '2024-09-12'),
  ('61045', 'BLUEBIRD 3', 'ASTS', '2024-09-12'),
  ('61048', 'BLUEBIRD 2', 'ASTS', '2024-09-12'),
  ('61047', 'BLUEBIRD 1', 'ASTS', '2024-09-12'),
  ('53807', 'BLUEWALKER 3', 'ASTS', '2022-09-10')
ON CONFLICT (norad_id) DO UPDATE SET
  name = EXCLUDED.name,
  launch_date = EXCLUDED.launch_date;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Latest TLE freshness view
CREATE OR REPLACE VIEW satellite_freshness AS
SELECT
  s.norad_id,
  s.name,
  s.tle_epoch,
  s.updated_at,
  EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 AS hours_since_epoch,
  CASE
    WHEN s.tle_epoch IS NULL THEN 'NO_DATA'
    WHEN EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 < 6 THEN 'FRESH'
    WHEN EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 < 12 THEN 'OK'
    WHEN EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 < 24 THEN 'STALE'
    ELSE 'CRITICAL'
  END AS freshness_status
FROM satellites s
WHERE s.constellation = 'ASTS'
ORDER BY s.tle_epoch DESC NULLS LAST;

-- B* trend view (last 30 days)
CREATE OR REPLACE VIEW bstar_trends AS
SELECT
  norad_id,
  epoch,
  bstar,
  LAG(bstar) OVER (PARTITION BY norad_id ORDER BY epoch) AS prev_bstar,
  bstar - LAG(bstar) OVER (PARTITION BY norad_id ORDER BY epoch) AS bstar_delta
FROM tle_history
WHERE epoch > now() - INTERVAL '30 days'
ORDER BY norad_id, epoch DESC;
