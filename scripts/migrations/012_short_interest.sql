-- Short interest historical data from Yahoo Finance / FINRA
-- Updated biweekly by short_interest_worker.py

CREATE TABLE IF NOT EXISTS short_interest (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  symbol TEXT NOT NULL DEFAULT 'ASTS',
  shares_short BIGINT NOT NULL,
  short_ratio NUMERIC(6,2),
  short_pct_float NUMERIC(6,2),
  short_pct_outstanding NUMERIC(6,2),
  shares_short_prior BIGINT,
  shares_outstanding BIGINT,
  float_shares BIGINT,
  report_date DATE,
  fetched_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for widget query (latest by report_date)
CREATE INDEX IF NOT EXISTS idx_short_interest_symbol_date
  ON short_interest (symbol, report_date DESC);
