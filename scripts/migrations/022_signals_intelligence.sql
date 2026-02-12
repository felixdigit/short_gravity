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
  WHEN signal_type IN ('short_interest_spike') THEN 'market'
  WHEN signal_type IN ('sentiment_shift', 'cross_source') THEN 'community'
  WHEN signal_type = 'new_content' THEN 'corporate'
  WHEN signal_type = 'patent_deployment' THEN 'ip'
  ELSE 'corporate'
END
WHERE category IS NULL;

-- Index for dashboard queries
CREATE INDEX IF NOT EXISTS idx_signals_category ON signals(category);
CREATE INDEX IF NOT EXISTS idx_signals_category_severity ON signals(category, severity);
