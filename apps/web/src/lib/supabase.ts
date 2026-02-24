import { createClient, SupabaseClient } from '@supabase/supabase-js'

/**
 * Sanitize search query to prevent SQL injection in ilike patterns.
 * Escapes special characters and enforces max length.
 */
export function sanitizeSearchQuery(query: string, maxLength: number = 100): string {
  // Trim and limit length
  let sanitized = query.trim().slice(0, maxLength);

  // Escape special PostgreSQL pattern characters
  sanitized = sanitized
    .replace(/\\/g, '\\\\')  // Escape backslashes first
    .replace(/%/g, '\\%')    // Escape percent
    .replace(/_/g, '\\_')    // Escape underscore
    .replace(/'/g, "''");    // Escape single quotes

  return sanitized;
}

let supabaseInstance: SupabaseClient | null = null;
let serviceInstance: SupabaseClient | null = null;

function getSupabase(): SupabaseClient {
  if (!supabaseInstance) {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error('Missing Supabase environment variables');
    }

    supabaseInstance = createClient(supabaseUrl, supabaseAnonKey);
  }
  return supabaseInstance;
}

/**
 * Server-side Supabase client with service key.
 * Throws if SUPABASE_SERVICE_KEY is not set — never falls back to anon key.
 */
export function getServiceClient(): SupabaseClient {
  if (!serviceInstance) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_KEY;

    if (!url) throw new Error('Missing NEXT_PUBLIC_SUPABASE_URL');
    if (!key) throw new Error('Missing SUPABASE_SERVICE_KEY — server routes require the service key');

    serviceInstance = createClient(url, key);
  }
  return serviceInstance;
}

export const supabase = new Proxy({} as SupabaseClient, {
  get(_, prop) {
    return getSupabase()[prop as keyof SupabaseClient];
  }
});

/**
 * Get current server time from Supabase
 * This function is a no-op for now - returns local time
 * The real fix is to ensure Vercel edge functions have correct clocks
 */
export async function getSupabaseServerTime(): Promise<Date> {
  return new Date();
}

// ============================================================================
// FILINGS
// ============================================================================

export interface DBFiling {
  id: string;
  accession_number: string;
  form: string;
  filing_date: string;
  report_date: string | null;
  items: string | null;
  file_size: number | null;
  url: string;
  summary: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface DBFilingWithContent extends DBFiling {
  content_text: string | null;
  content_length: number | null;
}

/**
 * Get filings feed from Supabase
 */
export async function getFilingsFeed(options: {
  limit?: number;
  form?: string;
  since?: string;
} = {}): Promise<DBFiling[]> {
  const { limit = 20, form, since } = options;

  let query = supabase
    .from('filings')
    .select('id, accession_number, form, filing_date, report_date, items, file_size, url, summary, status, created_at, updated_at')
    .eq('status', 'completed')
    .order('filing_date', { ascending: false })
    .limit(limit);

  if (form) {
    query = query.or(`form.eq.${form},form.eq.${form}/A`);
  }

  if (since) {
    query = query.gte('filing_date', since);
  }

  const { data, error } = await query;

  if (error) {
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch filings');
  }

  return data || [];
}

/**
 * Get single filing with full content
 */
export async function getFilingByAccession(accessionNumber: string): Promise<DBFilingWithContent | null> {
  const { data, error } = await supabase
    .from('filings')
    .select('*')
    .eq('accession_number', accessionNumber)
    .single();

  if (error) {
    if (error.code === 'PGRST116') {
      return null; // Not found
    }
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch filing');
  }

  return data;
}

/**
 * Get count of filings by status
 */
export async function getFilingsCount(): Promise<{ total: number; completed: number; pending: number }> {
  const [
    { count: total },
    { count: completed },
    { count: pending },
  ] = await Promise.all([
    supabase.from('filings').select('*', { count: 'exact', head: true }),
    supabase.from('filings').select('*', { count: 'exact', head: true }).eq('status', 'completed'),
    supabase.from('filings').select('*', { count: 'exact', head: true }).eq('status', 'pending'),
  ]);

  return {
    total: total || 0,
    completed: completed || 0,
    pending: pending || 0,
  };
}

// ============================================================================
// SATELLITES
// ============================================================================

export interface DBSatellite {
  norad_id: string;
  name: string;
  tle_line0: string | null;
  tle_line1: string | null;
  tle_line2: string | null;
  tle_epoch: string | null;
  bstar: string | null;
  mean_motion: string | null;
  mean_motion_dot: string | null;
  inclination: string | null;
  eccentricity: string | null;
  ra_of_asc_node: string | null;
  semimajor_axis: string | null;
  period_minutes: string | null;
  apoapsis_km: string | null;
  periapsis_km: string | null;
  rev_at_epoch: number | null;
  tle_source: string | null;
  raw_gp: Record<string, unknown> | null;
  updated_at: string;
  // Computed field from database query (PostgreSQL NOW() - tle_epoch)
  hours_old?: number;
}

export interface DBTLEHistory {
  id: string;
  norad_id: string;
  epoch: string;
  tle_line0: string | null;
  tle_line1: string;
  tle_line2: string;
  bstar: string | null;
  mean_motion: string | null;
  mean_motion_dot: string | null;
  eccentricity: string | null;
  inclination: string | null;
  ra_of_asc_node: string | null;
  arg_of_pericenter: string | null;
  mean_anomaly: string | null;
  semimajor_axis: string | null;
  period_minutes: string | null;
  apoapsis_km: string | null;
  periapsis_km: string | null;
  source: string;
  raw_gp: Record<string, unknown>;
}

/**
 * Get current satellite data by NORAD IDs
 */
export async function getSatellitesByNoradIds(noradIds: string[]): Promise<DBSatellite[]> {
  // Create fresh client to avoid any caching issues
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error('Missing Supabase credentials');
  }

  // Use direct fetch instead of Supabase client to bypass any caching
  const selectCols = 'norad_id,name,tle_line0,tle_line1,tle_line2,tle_epoch,bstar,mean_motion,mean_motion_dot,inclination,eccentricity,ra_of_asc_node,semimajor_axis,period_minutes,apoapsis_km,periapsis_km,rev_at_epoch,tle_source,updated_at';
  const response = await fetch(
    `${url}/rest/v1/satellites?select=${selectCols}&norad_id=in.(${noradIds.join(',')})`,
    {
      headers: {
        'apikey': key,
        'Authorization': `Bearer ${key}`,
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
      },
      cache: 'no-store',
    }
  );

  if (!response.ok) {
    console.error('Supabase fetch error:', response.status, response.statusText);
    throw new Error('Failed to fetch satellites');
  }

  const data = await response.json();
  return data || [];
}

/**
 * Get all ASTS constellation satellites
 */
export async function getASTSSatellites(): Promise<DBSatellite[]> {
  const { data, error } = await supabase
    .from('satellites')
    .select('*')
    .eq('constellation', 'ASTS')
    .order('tle_epoch', { ascending: false });

  if (error) {
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch ASTS satellites');
  }

  return data || [];
}

/**
 * Get TLE history for a satellite
 */
export async function getTLEHistory(noradId: string, options: {
  limit?: number;
  since?: string;
} = {}): Promise<DBTLEHistory[]> {
  const { limit = 100, since } = options;

  // Use direct fetch to bypass Supabase client caching
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error('Missing Supabase credentials');
  }

  // Build query params
  const params = new URLSearchParams({
    select: '*',
    norad_id: `eq.${noradId}`,
    order: 'epoch.desc',
    limit: limit.toString(),
  });

  if (since) {
    params.append('epoch', `gte.${since}`);
  }

  const response = await fetch(
    `${url}/rest/v1/tle_history?${params.toString()}`,
    {
      headers: {
        'apikey': key,
        'Authorization': `Bearer ${key}`,
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
      },
      cache: 'no-store',
    }
  );

  if (!response.ok) {
    console.error('Supabase fetch error:', response.status, response.statusText);
    throw new Error('Failed to fetch TLE history');
  }

  const data = await response.json();
  return data || [];
}

/**
 * Get satellite freshness status
 */
export async function getSatelliteFreshness(): Promise<{
  norad_id: string;
  name: string;
  tle_epoch: string | null;
  hours_since_epoch: number | null;
  freshness_status: 'FRESH' | 'OK' | 'STALE' | 'CRITICAL' | 'NO_DATA';
}[]> {
  const { data, error } = await supabase
    .from('satellite_freshness')
    .select('*');

  if (error) {
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch satellite freshness');
  }

  return data || [];
}

/**
 * Get B* trends for a satellite (last 30 days)
 */
export async function getBstarTrends(noradId: string): Promise<{
  norad_id: string;
  epoch: string;
  bstar: string | null;
  prev_bstar: string | null;
  bstar_delta: string | null;
}[]> {
  const { data, error } = await supabase
    .from('bstar_trends')
    .select('*')
    .eq('norad_id', noradId)
    .order('epoch', { ascending: false });

  if (error) {
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch B* trends');
  }

  return data || [];
}

// ============================================================================
// GLOSSARY
// ============================================================================

export interface DBGlossaryTerm {
  id: string;
  term: string;
  normalized_term: string;
  aliases: string[];
  definition: string;
  definition_source: 'extracted' | 'curated' | 'hybrid';
  category: 'financial' | 'technical' | 'regulatory' | 'company' | 'partnership' | 'acronym';
  subcategory: string | null;
  first_seen_date: string | null;
  mention_count: number;
  importance: 'low' | 'normal' | 'high' | 'critical';
  context_summary: string | null;
  related_terms: string[];
  status: 'draft' | 'review' | 'published';
  created_at: string;
  updated_at: string;
}

export interface DBGlossaryCitation {
  id: string;
  term_id: string;
  sec_accession_number: string | null;
  fcc_file_number: string | null;
  excerpt: string;
  filing_date: string;
  filing_type: string;
  relevance_score: number;
  is_primary: boolean;
  created_at: string;
}

/**
 * Search glossary terms
 */
export async function searchGlossaryTerms(options: {
  query?: string;
  category?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<DBGlossaryTerm[]> {
  const { query, category, limit = 50, offset = 0 } = options;

  let q = supabase
    .from('glossary_terms')
    .select('*')
    .eq('status', 'published')
    .order('importance', { ascending: false })
    .order('mention_count', { ascending: false })
    .range(offset, offset + limit - 1);

  if (query && query.length >= 2) {
    const sanitized = sanitizeSearchQuery(query);
    q = q.or(`term.ilike.%${sanitized}%,definition.ilike.%${sanitized}%,normalized_term.ilike.%${sanitized}%`);
  }

  if (category) {
    q = q.eq('category', category);
  }

  const { data, error } = await q;

  if (error) {
    console.error('Supabase error:', error);
    throw new Error('Failed to search glossary');
  }

  return data || [];
}

/**
 * Get single glossary term by ID
 */
export async function getGlossaryTerm(termId: string): Promise<DBGlossaryTerm | null> {
  const { data, error } = await supabase
    .from('glossary_terms')
    .select('*')
    .eq('id', termId)
    .eq('status', 'published')
    .single();

  if (error) {
    if (error.code === 'PGRST116') {
      return null;
    }
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch glossary term');
  }

  return data;
}

/**
 * Get citations for a glossary term
 */
export async function getGlossaryCitations(termId: string): Promise<DBGlossaryCitation[]> {
  const { data, error } = await supabase
    .from('glossary_citations')
    .select('*')
    .eq('term_id', termId)
    .order('is_primary', { ascending: false })
    .order('filing_date', { ascending: false });

  if (error) {
    console.error('Supabase error:', error);
    throw new Error('Failed to fetch citations');
  }

  return data || [];
}

/**
 * Get glossary category counts
 */
export async function getGlossaryCategories(): Promise<{ category: string; count: number }[]> {
  // Use head:true count queries per category instead of fetching all rows
  const categories = ['financial', 'technical', 'regulatory', 'company', 'partnership', 'acronym'];
  const results = await Promise.all(
    categories.map(async (category) => {
      const { count, error } = await supabase
        .from('glossary_terms')
        .select('*', { count: 'exact', head: true })
        .eq('status', 'published')
        .eq('category', category);
      if (error) return { category, count: 0 };
      return { category, count: count || 0 };
    })
  );

  return results.filter(c => c.count > 0).sort((a, b) => b.count - a.count);
}

/**
 * Get total glossary term count
 */
export async function getGlossaryCount(): Promise<number> {
  const { count, error } = await supabase
    .from('glossary_terms')
    .select('*', { count: 'exact', head: true })
    .eq('status', 'published');

  if (error) {
    console.error('Supabase error:', error);
    return 0;
  }

  return count || 0;
}
