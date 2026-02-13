-- Migration 025: Fix Source Divergence View — Epoch Matching
-- The original view (018) compared latest CelesTrak vs Space-Track B* per satellite
-- WITHOUT checking if the epochs were close. A 3-day epoch gap makes the B* comparison
-- meaningless. This fix requires epochs to be within 6 hours of each other.
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
  EXTRACT(EPOCH FROM (ct.epoch::timestamp - st.epoch::timestamp)) / 3600.0 AS epoch_gap_hours,
  CASE WHEN ABS(ct.bstar::numeric - st.bstar::numeric) > 0.0001 THEN true ELSE false END AS diverged
FROM latest_ct ct
JOIN latest_st st ON ct.norad_id = st.norad_id
WHERE ABS(EXTRACT(EPOCH FROM (ct.epoch::timestamp - st.epoch::timestamp))) < 21600; -- 6 hours in seconds
