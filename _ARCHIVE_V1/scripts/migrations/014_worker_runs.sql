-- Worker run logging for pipeline monitoring dashboard
-- Each GitHub Actions workflow logs its completion here

CREATE TABLE IF NOT EXISTS worker_runs (
  id BIGSERIAL PRIMARY KEY,
  worker_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unknown',
  run_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_worker_runs_name_created ON worker_runs(worker_name, created_at DESC);

-- RPC: Get brain_chunks stats grouped by source_table (avoids N+1 queries)
CREATE OR REPLACE FUNCTION brain_chunk_stats()
RETURNS TABLE(source_table TEXT, chunk_count BIGINT) AS $$
  SELECT source_table, count(*) as chunk_count
  FROM brain_chunks
  GROUP BY source_table
  ORDER BY chunk_count DESC;
$$ LANGUAGE sql STABLE;

-- RPC: Get all pipeline table counts in one call
CREATE OR REPLACE FUNCTION pipeline_table_counts()
RETURNS JSON AS $$
  SELECT json_build_object(
    'patents', (SELECT count(*) FROM patents),
    'patent_claims', (SELECT count(*) FROM patent_claims),
    'filings', (SELECT count(*) FROM filings),
    'fcc_filings', (SELECT count(*) FROM fcc_filings),
    'press_releases', (SELECT count(*) FROM press_releases),
    'earnings_transcripts', (SELECT count(*) FROM inbox WHERE source = 'earnings_call'),
    'short_interest', (SELECT count(*) FROM short_interest),
    'cash_position', (SELECT count(*) FROM cash_position)
  );
$$ LANGUAGE sql STABLE;
