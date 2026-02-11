-- Brain conversations: persistent chat history per anonymous session
-- Session = browser cookie (sg_session), no auth required

CREATE TABLE IF NOT EXISTS brain_conversations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id TEXT NOT NULL,
  title TEXT,                    -- Auto-generated from first query
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fast lookup: user's conversations, most recent first
CREATE INDEX idx_brain_conversations_session
  ON brain_conversations(session_id, updated_at DESC);

-- RLS: off (no auth, anonymous access via service key)
ALTER TABLE brain_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service key full access" ON brain_conversations
  FOR ALL USING (true) WITH CHECK (true);
