-- Migration 005: Patent Claims & Family Linking
-- Enables capture of ALL individual patent claims (~3,800 for ASTS)
-- Links patents to families (36 families per official disclosure)

-- Add family_id directly to patents table for easy grouping
ALTER TABLE patents ADD COLUMN IF NOT EXISTS family_id TEXT;
CREATE INDEX IF NOT EXISTS idx_patents_family_id ON patents(family_id);

-- Individual claims table for full text storage and RAG search
CREATE TABLE IF NOT EXISTS patent_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_number TEXT NOT NULL,
    claim_number INTEGER NOT NULL,
    claim_text TEXT NOT NULL,
    claim_type TEXT CHECK (claim_type IN ('independent', 'dependent')),
    depends_on INTEGER[], -- Array of claim numbers this claim depends on
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(patent_number, claim_number)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_patent_claims_patent ON patent_claims(patent_number);
CREATE INDEX IF NOT EXISTS idx_patent_claims_type ON patent_claims(claim_type);

-- Full-text search on claim text for RAG
CREATE INDEX IF NOT EXISTS idx_patent_claims_fts ON patent_claims
    USING GIN(to_tsvector('english', claim_text));

-- Row Level Security
ALTER TABLE patent_claims ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Patent claims are publicly readable"
    ON patent_claims FOR SELECT
    USING (true);

-- Service role full access for workers
CREATE POLICY "Service role can manage patent claims"
    ON patent_claims FOR ALL
    USING (auth.role() = 'service_role');

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_patent_claims_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS patent_claims_updated_at ON patent_claims;
CREATE TRIGGER patent_claims_updated_at
    BEFORE UPDATE ON patent_claims
    FOR EACH ROW
    EXECUTE FUNCTION update_patent_claims_updated_at();

-- Comment for documentation
COMMENT ON TABLE patent_claims IS 'Individual patent claims for ASTS IP portfolio. ~3,800 claims across 36 families.';
COMMENT ON COLUMN patent_claims.claim_type IS 'independent = standalone claim, dependent = references another claim';
COMMENT ON COLUMN patent_claims.depends_on IS 'Array of claim numbers this dependent claim references';
COMMENT ON COLUMN patents.family_id IS 'EPO DOCDB family ID linking related patents across jurisdictions';
