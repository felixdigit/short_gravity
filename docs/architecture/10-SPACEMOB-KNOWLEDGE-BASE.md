# Spacemob Knowledge Base Schema

**Purpose:** Store, query, and compound Spacemob intelligence over time.

**Use cases:**
1. Claude context for research and content creation
2. Timeline UI on the website
3. Training corpus for future Spacemob AI model
4. Historical archive (digital museum)

---

## Core Tables

### `voices`
Curated X accounts and Reddit users to track.

```sql
CREATE TABLE voices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL CHECK (platform IN ('x', 'reddit', 'other')),
  handle TEXT NOT NULL,
  display_name TEXT,
  bio TEXT,
  follower_count INTEGER,
  focus_area TEXT, -- e.g., 'technical', 'fundamental', 'sentiment', 'insider'
  reliability_score INTEGER CHECK (reliability_score BETWEEN 1 AND 10),
  notes TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(platform, handle)
);
```

### `posts`
Tweets, Reddit posts/comments — the raw social content.

```sql
CREATE TABLE posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform TEXT NOT NULL CHECK (platform IN ('x', 'reddit')),
  platform_id TEXT NOT NULL, -- Original tweet ID or Reddit post ID
  voice_id UUID REFERENCES voices(id),
  content TEXT NOT NULL,
  url TEXT,
  posted_at TIMESTAMPTZ NOT NULL,

  -- Engagement metrics (at time of capture)
  likes INTEGER,
  reposts INTEGER, -- retweets or Reddit score
  replies INTEGER,

  -- Classification
  is_about_asts BOOLEAN DEFAULT true,
  topics TEXT[], -- e.g., ['spectrum', 'partnership', 'technical', 'earnings']
  sentiment TEXT CHECK (sentiment IN ('bullish', 'bearish', 'neutral', 'mixed')),
  significance TEXT CHECK (significance IN ('low', 'medium', 'high', 'critical')),

  -- For threads/replies
  parent_id UUID REFERENCES posts(id),
  thread_id UUID, -- Groups posts in same thread

  -- AI-generated
  summary TEXT,
  key_points TEXT[],

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(platform, platform_id)
);

CREATE INDEX idx_posts_posted_at ON posts(posted_at DESC);
CREATE INDEX idx_posts_voice_id ON posts(voice_id);
CREATE INDEX idx_posts_topics ON posts USING GIN(topics);
CREATE INDEX idx_posts_significance ON posts(significance);
```

### `filings`
SEC filings and other regulatory documents.

```sql
CREATE TABLE filings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company TEXT NOT NULL, -- 'ASTS' or other company ticker
  filing_type TEXT NOT NULL, -- '10-K', '10-Q', '8-K', 'S-1', etc.
  filed_at TIMESTAMPTZ NOT NULL,
  period_end DATE, -- For periodic reports
  url TEXT NOT NULL,

  -- Content
  title TEXT,
  raw_text TEXT, -- Full text for search/training

  -- AI-generated
  summary TEXT,
  key_points TEXT[],
  asts_mentions TEXT[], -- Relevant excerpts if not ASTS filing
  material_changes TEXT[],

  -- Classification
  significance TEXT CHECK (significance IN ('low', 'medium', 'high', 'critical')),
  topics TEXT[],

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(company, filing_type, filed_at)
);

CREATE INDEX idx_filings_filed_at ON filings(filed_at DESC);
CREATE INDEX idx_filings_company ON filings(company);
CREATE INDEX idx_filings_type ON filings(filing_type);
```

### `events`
Curated timeline of key moments — the digital museum.

```sql
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at TIMESTAMPTZ NOT NULL,

  -- Content
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  detailed_content TEXT, -- Longer form for detail view

  -- Classification
  category TEXT NOT NULL CHECK (category IN (
    'launch', 'partnership', 'spectrum', 'regulatory',
    'earnings', 'technical', 'market', 'community', 'other'
  )),
  significance TEXT CHECK (significance IN ('low', 'medium', 'high', 'critical')),

  -- Sources
  source_urls TEXT[],
  source_post_ids UUID[], -- References to posts table
  source_filing_ids UUID[], -- References to filings table

  -- Media
  image_url TEXT,

  -- For timeline UI
  is_featured BOOLEAN DEFAULT false,
  display_order INTEGER, -- For manual ordering within same day

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_events_occurred_at ON events(occurred_at DESC);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_featured ON events(is_featured) WHERE is_featured = true;
```

### `alpha`
Extracted insights and alpha nuggets.

```sql
CREATE TABLE alpha (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  discovered_at TIMESTAMPTZ DEFAULT now(),

  -- Content
  title TEXT NOT NULL,
  insight TEXT NOT NULL,
  why_it_matters TEXT,

  -- Classification
  category TEXT CHECK (category IN (
    'spectrum', 'partnership', 'technical', 'regulatory',
    'competitive', 'financial', 'operational', 'other'
  )),
  confidence TEXT CHECK (confidence IN ('speculation', 'likely', 'confirmed')),
  significance TEXT CHECK (significance IN ('low', 'medium', 'high', 'critical')),

  -- Sources
  source_post_ids UUID[],
  source_filing_ids UUID[],
  source_urls TEXT[],

  -- Status
  is_validated BOOLEAN DEFAULT false,
  validated_at TIMESTAMPTZ,
  invalidated_at TIMESTAMPTZ,
  invalidation_reason TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_alpha_discovered_at ON alpha(discovered_at DESC);
CREATE INDEX idx_alpha_category ON alpha(category);
CREATE INDEX idx_alpha_significance ON alpha(significance);
```

### `entities`
People, companies, and organizations mentioned in the knowledge base.

```sql
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL CHECK (entity_type IN (
    'person', 'company', 'organization', 'satellite', 'spectrum_band'
  )),
  name TEXT NOT NULL,
  ticker TEXT, -- For companies
  description TEXT,

  -- Relationships to ASTS
  relationship TEXT, -- e.g., 'partner', 'competitor', 'investor', 'executive'
  relationship_details TEXT,

  -- Metadata
  website TEXT,
  wikipedia_url TEXT,
  image_url TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(entity_type, name)
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_relationship ON entities(relationship);
```

### `entity_mentions`
Junction table linking content to entities.

```sql
CREATE TABLE entity_mentions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,

  -- Polymorphic reference
  post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
  filing_id UUID REFERENCES filings(id) ON DELETE CASCADE,
  event_id UUID REFERENCES events(id) ON DELETE CASCADE,
  alpha_id UUID REFERENCES alpha(id) ON DELETE CASCADE,

  context TEXT, -- The snippet where entity is mentioned
  created_at TIMESTAMPTZ DEFAULT now(),

  CHECK (
    (post_id IS NOT NULL)::int +
    (filing_id IS NOT NULL)::int +
    (event_id IS NOT NULL)::int +
    (alpha_id IS NOT NULL)::int = 1
  )
);

CREATE INDEX idx_entity_mentions_entity ON entity_mentions(entity_id);
CREATE INDEX idx_entity_mentions_post ON entity_mentions(post_id) WHERE post_id IS NOT NULL;
CREATE INDEX idx_entity_mentions_filing ON entity_mentions(filing_id) WHERE filing_id IS NOT NULL;
```

---

## Utility Tables

### `scrape_jobs`
Track ingestion/scraping progress.

```sql
CREATE TABLE scrape_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type TEXT NOT NULL, -- 'x_timeline', 'reddit_subreddit', 'sec_filings'
  target TEXT NOT NULL, -- handle, subreddit, or company
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),

  -- Progress
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  items_processed INTEGER DEFAULT 0,
  items_total INTEGER,
  last_cursor TEXT, -- For pagination
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### `training_exports`
Track exports for model training.

```sql
CREATE TABLE training_exports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  export_type TEXT NOT NULL, -- 'full', 'incremental', 'filtered'
  filters JSONB, -- What was included

  -- Stats
  posts_count INTEGER,
  filings_count INTEGER,
  events_count INTEGER,
  alpha_count INTEGER,
  total_tokens_estimate INTEGER,

  -- File
  file_url TEXT,
  file_size_bytes BIGINT,

  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Views for Common Queries

### Timeline View (for UI)
```sql
CREATE VIEW timeline_view AS
SELECT
  id,
  occurred_at,
  title,
  description,
  category,
  significance,
  is_featured,
  image_url,
  source_urls
FROM events
ORDER BY occurred_at DESC;
```

### Recent Alpha
```sql
CREATE VIEW recent_alpha AS
SELECT
  a.*,
  array_agg(DISTINCT p.content) FILTER (WHERE p.id IS NOT NULL) as source_posts
FROM alpha a
LEFT JOIN posts p ON p.id = ANY(a.source_post_ids)
WHERE a.invalidated_at IS NULL
GROUP BY a.id
ORDER BY a.discovered_at DESC;
```

---

## Row Level Security (RLS)

For now, public read access, authenticated write:

```sql
-- Enable RLS on all tables
ALTER TABLE voices ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE filings ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE alpha ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- Public read access
CREATE POLICY "Public read access" ON voices FOR SELECT USING (true);
CREATE POLICY "Public read access" ON posts FOR SELECT USING (true);
CREATE POLICY "Public read access" ON filings FOR SELECT USING (true);
CREATE POLICY "Public read access" ON events FOR SELECT USING (true);
CREATE POLICY "Public read access" ON alpha FOR SELECT USING (true);
CREATE POLICY "Public read access" ON entities FOR SELECT USING (true);

-- Service role write access (for ingestion scripts)
CREATE POLICY "Service write access" ON voices FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write access" ON posts FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write access" ON filings FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write access" ON events FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write access" ON alpha FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service write access" ON entities FOR ALL USING (auth.role() = 'service_role');
```

---

## Storage Estimates

| Table | Rows (estimate) | Size/row | Total |
|-------|-----------------|----------|-------|
| posts | 50,000-100,000 | ~2KB | 100-200 MB |
| filings | 500 | ~50KB | 25 MB |
| events | 200 | ~5KB | 1 MB |
| alpha | 1,000 | ~2KB | 2 MB |
| voices | 50 | ~1KB | <1 MB |
| entities | 500 | ~1KB | <1 MB |

**Total estimate:** ~150-250 MB (well within free tier's 500 MB)

---

## Next Steps

1. Create Supabase project
2. Run this schema (can paste into SQL editor)
3. Add credentials to `.env.local`
4. Install `@supabase/supabase-js`
5. Create database client utility
6. Build API routes for CRUD operations
