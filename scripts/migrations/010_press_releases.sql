-- Press Releases table
-- Stores official AST SpaceMobile press releases from BusinessWire / IR page

CREATE TABLE IF NOT EXISTS press_releases (
  id BIGSERIAL PRIMARY KEY,
  source_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  url TEXT,
  category TEXT DEFAULT 'announcement',
  tags JSONB DEFAULT '[]',
  content_text TEXT,
  summary TEXT,
  status TEXT DEFAULT 'completed',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_press_releases_published ON press_releases(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_press_releases_category ON press_releases(category);
CREATE INDEX IF NOT EXISTS idx_press_releases_source_id ON press_releases(source_id);

-- Full-text search
ALTER TABLE press_releases ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(summary, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(content_text, '')), 'C')
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_press_releases_fts ON press_releases USING GIN(fts);

-- RLS
ALTER TABLE press_releases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read" ON press_releases FOR SELECT USING (true);
CREATE POLICY "Allow service insert" ON press_releases FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service update" ON press_releases FOR UPDATE USING (true);
