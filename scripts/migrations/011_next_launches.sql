-- Next Launches table for tracking upcoming ASTS satellite launches
-- Used by the LaunchCountdown HUD widget

CREATE TABLE IF NOT EXISTS next_launches (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  mission TEXT NOT NULL,
  provider TEXT,
  site TEXT,
  target_date TIMESTAMPTZ,
  status TEXT DEFAULT 'SCHEDULED',
  satellite_count INT,
  notes TEXT,
  source_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for widget query (next upcoming launch)
CREATE INDEX IF NOT EXISTS idx_next_launches_status_date
  ON next_launches (status, target_date ASC);

-- Seed with known launches from press releases and earnings calls
INSERT INTO next_launches (mission, provider, site, target_date, status, satellite_count, notes) VALUES
  ('FM1 BlueBird-1', 'ISRO', 'Sriharikota, India', '2025-12-23T00:00:00Z', 'LAUNCHED', 1, 'First Block-2 satellite, GSLV launch'),
  ('FM2 BlueBird-2', 'SpaceX', 'Cape Canaveral, FL', '2026-02-28T00:00:00Z', 'SCHEDULED', 1, 'Second Block-2 satellite, Falcon 9'),
  ('FM3-5 BlueBird 3-5', 'SpaceX', 'Cape Canaveral, FL', '2026-06-15T00:00:00Z', 'SCHEDULED', 3, 'Batch of 3 Block-2 satellites')
ON CONFLICT DO NOTHING;
