-- Glossary Terms and Citations
-- Stores extracted terms from ASTS filings for SpaceMob fact-checking

CREATE TABLE IF NOT EXISTS glossary_terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Term identification
  term TEXT NOT NULL,
  normalized_term TEXT NOT NULL,
  aliases TEXT[] DEFAULT '{}',

  -- Definition
  definition TEXT NOT NULL,
  definition_source TEXT DEFAULT 'extracted' CHECK (definition_source IN ('extracted', 'curated', 'hybrid')),

  -- Categorization
  category TEXT NOT NULL CHECK (category IN (
    'financial',
    'technical',
    'regulatory',
    'company',
    'partnership',
    'acronym'
  )),
  subcategory TEXT,

  -- Metadata
  first_seen_date DATE,
  mention_count INTEGER DEFAULT 0,
  importance TEXT DEFAULT 'normal' CHECK (importance IN ('low', 'normal', 'high', 'critical')),

  -- AI-generated context
  context_summary TEXT,
  related_terms TEXT[] DEFAULT '{}',

  -- Tracking
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'published')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(normalized_term)
);

-- Junction table: Citations linking terms to filings
CREATE TABLE IF NOT EXISTS glossary_citations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  term_id UUID NOT NULL REFERENCES glossary_terms(id) ON DELETE CASCADE,

  -- Source reference (one must be set)
  sec_accession_number TEXT,
  fcc_file_number TEXT,

  -- Citation context
  excerpt TEXT NOT NULL,
  filing_date DATE NOT NULL,
  filing_type TEXT NOT NULL,

  -- Quality
  relevance_score DECIMAL(3,2) DEFAULT 0.50,
  is_primary BOOLEAN DEFAULT false,

  created_at TIMESTAMPTZ DEFAULT now(),

  CHECK (
    (sec_accession_number IS NOT NULL AND fcc_file_number IS NULL) OR
    (sec_accession_number IS NULL AND fcc_file_number IS NOT NULL)
  )
);

-- Indexes for glossary_terms
CREATE INDEX IF NOT EXISTS idx_glossary_terms_normalized ON glossary_terms(normalized_term);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_category ON glossary_terms(category);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_status ON glossary_terms(status) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_glossary_terms_importance ON glossary_terms(importance) WHERE importance IN ('high', 'critical');

-- Full-text search on terms
CREATE INDEX IF NOT EXISTS idx_glossary_terms_fts ON glossary_terms USING GIN (
  to_tsvector('english', term || ' ' || COALESCE(definition, ''))
);

-- Indexes for glossary_citations
CREATE INDEX IF NOT EXISTS idx_glossary_citations_term ON glossary_citations(term_id);
CREATE INDEX IF NOT EXISTS idx_glossary_citations_sec ON glossary_citations(sec_accession_number) WHERE sec_accession_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_glossary_citations_fcc ON glossary_citations(fcc_file_number) WHERE fcc_file_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_glossary_citations_date ON glossary_citations(filing_date DESC);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_glossary_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS glossary_terms_updated_at ON glossary_terms;
CREATE TRIGGER glossary_terms_updated_at
  BEFORE UPDATE ON glossary_terms
  FOR EACH ROW
  EXECUTE FUNCTION update_glossary_updated_at();

-- RLS Policies
ALTER TABLE glossary_terms ENABLE ROW LEVEL SECURITY;
ALTER TABLE glossary_citations ENABLE ROW LEVEL SECURITY;

-- Public read access for published terms
CREATE POLICY "Public read published terms" ON glossary_terms
  FOR SELECT USING (status = 'published');

-- Service role full access
CREATE POLICY "Service role full access terms" ON glossary_terms
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access citations" ON glossary_citations
  FOR ALL USING (auth.role() = 'service_role');

-- Public read access for citations of published terms
CREATE POLICY "Public read citations" ON glossary_citations
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM glossary_terms
      WHERE glossary_terms.id = glossary_citations.term_id
      AND glossary_terms.status = 'published'
    )
  );
