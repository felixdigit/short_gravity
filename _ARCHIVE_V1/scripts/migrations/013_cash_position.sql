-- Cash position extracted from SEC filings
-- Updated by cash_position_worker.py after each 10-Q/10-K filing

CREATE TABLE IF NOT EXISTS cash_position (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  symbol TEXT NOT NULL DEFAULT 'ASTS',
  cash_and_equivalents BIGINT,
  restricted_cash BIGINT,
  total_cash_restricted BIGINT,
  available_liquidity BIGINT,
  quarterly_burn BIGINT,
  unit TEXT DEFAULT 'thousands',
  label TEXT,
  filing_form TEXT,
  filing_date DATE,
  accession_number TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cash_position_symbol_date
  ON cash_position (symbol, filing_date DESC);
