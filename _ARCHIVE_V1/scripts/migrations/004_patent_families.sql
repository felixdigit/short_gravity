-- AST SpaceMobile Patent Families Schema
-- Run via Supabase SQL Editor
-- Source: Espacenet (EPO) - global patent data

-- Patent families (unique inventions across jurisdictions)
CREATE TABLE IF NOT EXISTS patent_families (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  family_number TEXT UNIQUE NOT NULL,
  title TEXT,
  applicant TEXT DEFAULT 'AST & Science LLC',
  earliest_priority DATE,
  earliest_publication DATE,
  primary_publication TEXT,  -- e.g., US12345678B1
  primary_country TEXT,      -- e.g., US
  publication_count INTEGER DEFAULT 0,
  publications JSONB,        -- [{country, number, kind, full}, ...]
  inventors JSONB,           -- [{first, last, country}, ...]
  cpc_codes JSONB,           -- ["H04B7/185", ...]
  ipc_codes JSONB,           -- ["H04B7/185", ...]
  country_breakdown JSONB,   -- {"US": 3, "EP": 2, "KR": 1}
  source TEXT DEFAULT 'espacenet',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_patent_families_priority ON patent_families(earliest_priority DESC);
CREATE INDEX IF NOT EXISTS idx_patent_families_country ON patent_families(primary_country);

-- Enable RLS
ALTER TABLE patent_families ENABLE ROW LEVEL SECURITY;

-- Read access for all
CREATE POLICY "Allow read access to patent_families" ON patent_families
  FOR SELECT USING (true);

-- Service role full access
CREATE POLICY "Service role full access to patent_families" ON patent_families
  FOR ALL USING (auth.role() = 'service_role');

-- Updated_at trigger
DROP TRIGGER IF EXISTS update_patent_families_updated_at ON patent_families;
CREATE TRIGGER update_patent_families_updated_at
  BEFORE UPDATE ON patent_families
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
