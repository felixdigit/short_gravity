-- Earnings Calls Table
-- Stores quarterly earnings call metadata and transcripts
-- Run in Supabase Dashboard SQL Editor

CREATE TABLE IF NOT EXISTS earnings_calls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Identification
  company TEXT NOT NULL DEFAULT 'ASTS',
  fiscal_year INTEGER NOT NULL,
  fiscal_quarter INTEGER NOT NULL CHECK (fiscal_quarter BETWEEN 1 AND 4),

  -- Timing
  call_date DATE NOT NULL,
  call_time TIME,
  timezone TEXT DEFAULT 'America/New_York',

  -- Links
  webcast_url TEXT,
  presentation_url TEXT,
  press_release_url TEXT,
  filing_8k_url TEXT,

  -- Transcript (added manually)
  transcript TEXT,
  transcript_source TEXT,
  transcript_added_at TIMESTAMPTZ,

  -- AI-generated (from transcript)
  summary TEXT,
  key_points TEXT[],
  guidance TEXT[],
  notable_quotes TEXT[],

  -- Metadata
  duration_minutes INTEGER,
  participants TEXT[],

  -- Status
  status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'transcript_pending', 'complete')),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(company, fiscal_year, fiscal_quarter)
);

CREATE INDEX IF NOT EXISTS idx_earnings_calls_date ON earnings_calls(call_date DESC);
CREATE INDEX IF NOT EXISTS idx_earnings_calls_status ON earnings_calls(status);

ALTER TABLE earnings_calls ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON earnings_calls FOR SELECT USING (true);
CREATE POLICY "Service write access" ON earnings_calls FOR ALL USING (auth.role() = 'service_role');
