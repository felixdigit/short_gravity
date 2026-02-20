-- 019_signals.sql — Cross-source anomaly detection
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS signals (
  id          BIGSERIAL PRIMARY KEY,
  signal_type TEXT NOT NULL,          -- sentiment_shift, filing_cluster, fcc_status_change, cross_source, short_interest_spike, patent_deployment
  severity    TEXT NOT NULL DEFAULT 'medium',  -- low, medium, high, critical
  title       TEXT NOT NULL,          -- One-line headline
  description TEXT,                   -- Haiku-generated analysis (2-3 sentences)

  -- Cross-reference: which sources triggered this signal
  source_refs JSONB DEFAULT '[]',     -- [{table, id, title, date}] — the documents that contributed

  -- Quantitative context
  metrics     JSONB DEFAULT '{}',     -- signal-specific numbers (e.g., sentiment_7d, sentiment_30d, delta, z_score)

  -- Lifecycle
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at  TIMESTAMPTZ,            -- optional: signal becomes stale after this
  status      TEXT NOT NULL DEFAULT 'active',  -- active, acknowledged, expired, false_positive

  -- Dedup
  fingerprint TEXT UNIQUE,            -- hash of signal_type + key inputs to prevent duplicate signals

  -- Timestamps
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_signals_severity ON signals(severity);
CREATE INDEX IF NOT EXISTS idx_signals_detected ON signals(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_signals_active ON signals(status, detected_at DESC) WHERE status = 'active';

-- RLS
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read signals" ON signals
  FOR SELECT USING (true);

CREATE POLICY "Service insert signals" ON signals
  FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service update signals" ON signals
  FOR UPDATE USING (auth.role() = 'service_role');
