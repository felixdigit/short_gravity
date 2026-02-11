-- 021_profiles.sql
-- Auth profiles table for tiered access (free / full_spectrum)

CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'full_spectrum')),
  patreon_id TEXT UNIQUE,
  patreon_email TEXT,
  patreon_status TEXT, -- 'active_patron', 'declined_patron', 'former_patron', null
  patreon_linked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for tier lookups
CREATE INDEX idx_profiles_tier ON profiles(tier);
CREATE INDEX idx_profiles_patreon_id ON profiles(patreon_id) WHERE patreon_id IS NOT NULL;

-- RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users can read own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile (but not tier — that's service-role only via webhook)
CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Service role has full access (bypasses RLS by default)

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_profiles_updated_at();
