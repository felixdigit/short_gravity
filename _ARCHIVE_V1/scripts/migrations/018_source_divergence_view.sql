-- Migration 018: Source Divergence Detection View
-- Pairs latest CelesTrak vs Space-Track B* per satellite to detect divergence.
-- Run in Supabase SQL Editor.

DROP VIEW IF EXISTS source_divergence;

CREATE VIEW source_divergence AS
WITH latest_ct AS (
  SELECT DISTINCT ON (norad_id) norad_id, epoch, bstar
  FROM tle_history WHERE source = 'celestrak'
  ORDER BY norad_id, epoch DESC
),
latest_st AS (
  SELECT DISTINCT ON (norad_id) norad_id, epoch, bstar
  FROM tle_history WHERE source = 'spacetrack'
  ORDER BY norad_id, epoch DESC
)
SELECT ct.norad_id,
  ct.bstar AS ct_bstar, ct.epoch AS ct_epoch,
  st.bstar AS st_bstar, st.epoch AS st_epoch,
  ABS(ct.bstar::numeric - st.bstar::numeric) AS bstar_delta,
  CASE WHEN ABS(ct.bstar::numeric - st.bstar::numeric) > 0.0001 THEN true ELSE false END AS diverged
FROM latest_ct ct
JOIN latest_st st ON ct.norad_id = st.norad_id;
