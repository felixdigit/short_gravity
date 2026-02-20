-- Migration 017: TLE Source Tracking
-- Adds source provenance columns to tle_history and satellites tables
-- Allows storing BOTH CelesTrak and Space-Track data for the same epoch
-- Run in Supabase SQL Editor BEFORE deploying code changes

-- Add source columns
ALTER TABLE tle_history ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'unknown';
ALTER TABLE satellites ADD COLUMN IF NOT EXISTS tle_source TEXT DEFAULT 'unknown';

-- Backfill existing data from raw_gp JSONB
UPDATE tle_history SET source = raw_gp->>'_source'
  WHERE raw_gp->>'_source' IS NOT NULL AND source = 'unknown';
UPDATE satellites SET tle_source = raw_gp->>'_source'
  WHERE raw_gp->>'_source' IS NOT NULL AND tle_source = 'unknown';

-- Replace unique constraint: (norad_id, epoch) → (norad_id, epoch, source)
-- Allows storing BOTH CelesTrak and Space-Track for same epoch
ALTER TABLE tle_history DROP CONSTRAINT IF EXISTS tle_history_norad_id_epoch_key;
ALTER TABLE tle_history ADD CONSTRAINT tle_history_norad_epoch_source_key
  UNIQUE(norad_id, epoch, source);

-- Index for source-filtered queries
CREATE INDEX IF NOT EXISTS idx_tle_history_source ON tle_history(source);

-- Recreate views with new columns (DROP required — Postgres can't rename via CREATE OR REPLACE)
DROP VIEW IF EXISTS satellite_freshness;
CREATE VIEW satellite_freshness AS
SELECT s.norad_id, s.name, s.tle_epoch, s.tle_source, s.updated_at,
  EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 AS hours_since_epoch,
  CASE
    WHEN s.tle_epoch IS NULL THEN 'NO_DATA'
    WHEN EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 < 6 THEN 'FRESH'
    WHEN EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 < 12 THEN 'OK'
    WHEN EXTRACT(EPOCH FROM (now() - s.tle_epoch)) / 3600 < 24 THEN 'STALE'
    ELSE 'CRITICAL'
  END AS freshness_status
FROM satellites s WHERE s.constellation = 'ASTS'
ORDER BY s.tle_epoch DESC NULLS LAST;

DROP VIEW IF EXISTS bstar_trends;
CREATE VIEW bstar_trends AS
SELECT norad_id, source, epoch, bstar,
  LAG(bstar) OVER (PARTITION BY norad_id, source ORDER BY epoch) AS prev_bstar,
  bstar - LAG(bstar) OVER (PARTITION BY norad_id, source ORDER BY epoch) AS bstar_delta
FROM tle_history WHERE epoch > now() - INTERVAL '30 days'
ORDER BY norad_id, source, epoch DESC;
