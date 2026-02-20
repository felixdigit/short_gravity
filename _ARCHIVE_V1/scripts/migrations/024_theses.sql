-- Migration 024: Theses table
-- Persistent thesis analysis results for Thread 003 (Thesis Builder)
-- Uses session_id pattern (same as brain_conversations) for anonymous persistence

CREATE TABLE IF NOT EXISTS theses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL,
  statement TEXT NOT NULL,

  -- Results from the three brain queries
  supporting_prose TEXT,
  supporting_sources JSONB DEFAULT '[]'::jsonb,
  contradicting_prose TEXT,
  contradicting_sources JSONB DEFAULT '[]'::jsonb,
  synthesis_prose TEXT,
  synthesis_sources JSONB DEFAULT '[]'::jsonb,

  -- Status tracking
  status TEXT NOT NULL DEFAULT 'generating',  -- generating, complete, failed

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: public read (for shareable URLs), session-gated write
ALTER TABLE theses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "theses_public_read" ON theses FOR SELECT USING (true);
CREATE POLICY "theses_session_insert" ON theses FOR INSERT WITH CHECK (true);
CREATE POLICY "theses_session_update" ON theses FOR UPDATE USING (true);

-- Indexes
CREATE INDEX idx_theses_session ON theses (session_id, created_at DESC);
CREATE INDEX idx_theses_status ON theses (status) WHERE status = 'generating';
