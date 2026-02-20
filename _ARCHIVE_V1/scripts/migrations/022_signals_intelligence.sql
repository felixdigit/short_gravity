-- 022_signals_intelligence.sql — Unified Intelligence Feed
-- Adds investor-intent categories, confidence scores, and price impact tracking
-- Run in Supabase SQL Editor

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS category TEXT,
  ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
  ADD COLUMN IF NOT EXISTS price_impact_24h FLOAT;

-- Backfill categories for existing signal types
UPDATE signals SET category = CASE
  WHEN signal_type IN ('filing_cluster', 'fcc_status_change') THEN 'regulatory'
  WHEN signal_type IN ('short_interest_spike', 'sentiment_shift') THEN 'market'
  WHEN signal_type = 'cross_source' THEN 'community'
  WHEN signal_type IN ('new_content', 'earnings_language_shift') THEN 'corporate'
  WHEN signal_type IN ('patent_deployment', 'patent_regulatory_crossref') THEN 'ip'
  ELSE 'corporate'
END
WHERE category IS NULL;

-- Backfill confidence scores for existing signal types
UPDATE signals SET confidence_score = CASE
  WHEN signal_type = 'fcc_status_change' THEN 0.95
  WHEN signal_type = 'filing_cluster' THEN 0.90
  WHEN signal_type = 'patent_regulatory_crossref' THEN 0.85
  WHEN signal_type = 'cross_source' THEN 0.80
  WHEN signal_type = 'earnings_language_shift' THEN 0.75
  WHEN signal_type = 'short_interest_spike' THEN 0.70
  WHEN signal_type = 'sentiment_shift' THEN 0.60
  WHEN signal_type = 'new_content' THEN 0.50
  ELSE 0.50
END
WHERE confidence_score IS NULL;

-- Index for dashboard queries
CREATE INDEX IF NOT EXISTS idx_signals_category ON signals(category);
CREATE INDEX IF NOT EXISTS idx_signals_category_severity ON signals(category, severity);
