-- X/Twitter posts table
-- Stores ASTS-related tweets for sentiment tracking and intelligence

CREATE TABLE IF NOT EXISTS x_posts (
  id BIGSERIAL PRIMARY KEY,
  source_id TEXT UNIQUE NOT NULL,        -- 'x_{tweet_id}'
  tweet_id TEXT NOT NULL,
  author_id TEXT,
  author_username TEXT,
  author_name TEXT,
  content_text TEXT NOT NULL,
  published_at TIMESTAMPTZ,
  summary TEXT,                           -- Haiku one-liner
  sentiment TEXT,                         -- bullish/bearish/neutral/informational
  signal_type TEXT,                       -- breaking_news/insider_signal/analyst_take/official/community
  category TEXT DEFAULT 'general',        -- satellite_launch/partnership/regulatory/financing/earnings/general
  tags JSONB DEFAULT '[]',
  metrics JSONB DEFAULT '{}',            -- {retweets, likes, replies, quotes, impressions}
  conversation_id TEXT,
  in_reply_to_id TEXT,
  is_thread_root BOOLEAN DEFAULT FALSE,
  search_query TEXT,                      -- which query matched this tweet
  url TEXT,                               -- https://x.com/{user}/status/{id}
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_x_posts_published ON x_posts(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_x_posts_sentiment ON x_posts(sentiment);
CREATE INDEX IF NOT EXISTS idx_x_posts_signal_type ON x_posts(signal_type);
CREATE INDEX IF NOT EXISTS idx_x_posts_category ON x_posts(category);
CREATE INDEX IF NOT EXISTS idx_x_posts_author ON x_posts(author_username);
CREATE INDEX IF NOT EXISTS idx_x_posts_conversation ON x_posts(conversation_id);
CREATE INDEX IF NOT EXISTS idx_x_posts_tweet_id ON x_posts(tweet_id);

-- Full-text search (author weighted A, summary B, content C)
ALTER TABLE x_posts ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', COALESCE(author_username, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(summary, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(content_text, '')), 'C')
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_x_posts_fts ON x_posts USING GIN(fts);

-- RLS
ALTER TABLE x_posts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read" ON x_posts FOR SELECT USING (true);
CREATE POLICY "Allow service insert" ON x_posts FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow service update" ON x_posts FOR UPDATE USING (true);
