-- AST SpaceMobile Patents Schema
-- Run via Supabase SQL Editor

-- Granted patents
CREATE TABLE IF NOT EXISTS patents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patent_id TEXT UNIQUE NOT NULL,
  patent_title TEXT,
  patent_date DATE,
  patent_type TEXT,
  assignee_organization TEXT,
  claim_count INTEGER DEFAULT 0,
  cpc_codes JSONB,
  inventors JSONB,
  source TEXT DEFAULT 'patentsview',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pre-grant publications (pending applications)
CREATE TABLE IF NOT EXISTS patent_applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_number TEXT UNIQUE NOT NULL,
  publication_title TEXT,
  publication_date DATE,
  assignee_organization TEXT,
  claim_count INTEGER DEFAULT 0,
  cpc_codes JSONB,
  inventors JSONB,
  status TEXT DEFAULT 'pending',
  source TEXT DEFAULT 'patentsview',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_patents_date ON patents(patent_date DESC);
CREATE INDEX IF NOT EXISTS idx_patents_assignee ON patents(assignee_organization);
CREATE INDEX IF NOT EXISTS idx_patent_applications_date ON patent_applications(publication_date DESC);
CREATE INDEX IF NOT EXISTS idx_patent_applications_status ON patent_applications(status);

-- Enable Row Level Security
ALTER TABLE patents ENABLE ROW LEVEL SECURITY;
ALTER TABLE patent_applications ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated users
CREATE POLICY "Allow read access to patents" ON patents
  FOR SELECT USING (true);

CREATE POLICY "Allow read access to patent_applications" ON patent_applications
  FOR SELECT USING (true);

-- Allow service role full access
CREATE POLICY "Service role full access to patents" ON patents
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to patent_applications" ON patent_applications
  FOR ALL USING (auth.role() = 'service_role');

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_patents_updated_at ON patents;
CREATE TRIGGER update_patents_updated_at
  BEFORE UPDATE ON patents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_patent_applications_updated_at ON patent_applications;
CREATE TRIGGER update_patent_applications_updated_at
  BEFORE UPDATE ON patent_applications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
