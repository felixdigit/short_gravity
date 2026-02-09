-- Brain query analytics log
-- Tracks queries, source distribution, latency for search quality iteration

CREATE TABLE IF NOT EXISTS brain_query_log (
  id BIGSERIAL PRIMARY KEY,
  query TEXT NOT NULL,
  search_query TEXT,                    -- actual query sent to search (may be keyword-extracted)
  source_counts JSONB DEFAULT '{}',     -- {"patent": 2, "filing": 1, "x_post": 3}
  result_count INTEGER DEFAULT 0,
  has_url BOOLEAN DEFAULT FALSE,
  has_history BOOLEAN DEFAULT FALSE,
  has_image BOOLEAN DEFAULT FALSE,
  mode TEXT DEFAULT 'default',          -- 'default' or 'counter-thesis'
  latency_ms INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brain_query_log_created ON brain_query_log(created_at DESC);

ALTER TABLE brain_query_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access query log" ON brain_query_log
  FOR ALL USING (auth.role() = 'service_role');
