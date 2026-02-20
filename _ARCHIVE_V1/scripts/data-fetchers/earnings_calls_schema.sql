-- Earnings Calls Table
-- Stores quarterly earnings call metadata and transcripts
-- Transcripts are added manually by Gabriel

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
  webcast_url TEXT,           -- Link to audio replay if available
  presentation_url TEXT,       -- Link to investor presentation PDF
  press_release_url TEXT,      -- Link to earnings press release
  filing_8k_url TEXT,          -- Link to 8-K filing

  -- Transcript (added manually)
  transcript TEXT,             -- Full transcript text
  transcript_source TEXT,      -- 'manual', 'seeking_alpha', etc.
  transcript_added_at TIMESTAMPTZ,

  -- AI-generated (from transcript)
  summary TEXT,
  key_points TEXT[],
  guidance TEXT[],             -- Forward-looking statements
  notable_quotes TEXT[],       -- Quotable moments from management

  -- Metadata
  duration_minutes INTEGER,    -- Call duration
  participants TEXT[],         -- List of executives on call

  -- Status
  status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'transcript_pending', 'complete')),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(company, fiscal_year, fiscal_quarter)
);

CREATE INDEX idx_earnings_calls_date ON earnings_calls(call_date DESC);
CREATE INDEX idx_earnings_calls_status ON earnings_calls(status);

-- Enable RLS
ALTER TABLE earnings_calls ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Public read access" ON earnings_calls FOR SELECT USING (true);

-- Service role write access
CREATE POLICY "Service write access" ON earnings_calls FOR ALL USING (auth.role() = 'service_role');
