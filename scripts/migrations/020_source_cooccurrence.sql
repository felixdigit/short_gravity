-- Source co-occurrence: tracks which documents appear together in brain query contexts.
-- Over time this builds a knowledge graph of related sources.

CREATE TABLE IF NOT EXISTS source_cooccurrence (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source_a text NOT NULL,           -- e.g. "patent:US11718421"
  source_b text NOT NULL,           -- e.g. "fcc_filing:0909-EX-ST-2024"
  query_context text,               -- abbreviated query that linked them
  created_at timestamptz DEFAULT now()
);

-- Index for finding related sources
CREATE INDEX idx_cooccurrence_source_a ON source_cooccurrence (source_a);
CREATE INDEX idx_cooccurrence_source_b ON source_cooccurrence (source_b);

-- Composite index for pair lookups
CREATE INDEX idx_cooccurrence_pair ON source_cooccurrence (source_a, source_b);
