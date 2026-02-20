/**
 * @shortgravity/database — Package entrypoint
 *
 * Exports:
 *   1. Full Drizzle schema (tables + enums)
 *   2. Supabase client factory for service-role and anon access
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// ─── Schema re-exports ─────────────────────────────────────────────────────

export * from "./schema";

// ─── Supabase client ────────────────────────────────────────────────────────

export type { SupabaseClient };

let _serviceClient: SupabaseClient | null = null;
let _anonClient: SupabaseClient | null = null;

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required env var: ${key}`);
  }
  return value;
}

/** Service-role client — full access, bypasses RLS. Workers & crons only. */
export function getServiceClient(): SupabaseClient {
  if (!_serviceClient) {
    _serviceClient = createClient(
      requireEnv("SUPABASE_URL"),
      requireEnv("SUPABASE_SERVICE_KEY"),
      { auth: { persistSession: false } },
    );
  }
  return _serviceClient;
}

/** Anon client — respects RLS. Frontend & user-facing routes. */
export function getAnonClient(): SupabaseClient {
  if (!_anonClient) {
    _anonClient = createClient(
      requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
      requireEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
    );
  }
  return _anonClient;
}
