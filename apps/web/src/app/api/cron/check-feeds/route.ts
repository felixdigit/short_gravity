/**
 * API Route: Check SEC and GlobeNewswire RSS feeds for new ASTS filings/PRs
 * POST /api/cron/check-feeds
 *
 * Called by Vercel cron every 5 minutes.
 * Sends Discord notification when new items are detected.
 *
 * Deduplication: checks press_releases.source_id for GlobeNewswire items
 * and filings.accession_number for SEC items (no feed_seen table needed).
 */

import { NextRequest, NextResponse } from 'next/server';
import { createHash } from 'crypto';
import { createApiHandler } from '@/lib/api/handler';
import { getServiceClient } from '@/lib/supabase';

export const dynamic = 'force-dynamic';

// Config
const ASTS_CIK = '0001780312';
const SEC_RSS_URL = `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${ASTS_CIK}&type=&dateb=&owner=include&count=10&output=atom`;
const GLOBENEWSWIRE_RSS_URL = 'https://www.globenewswire.com/RssFeed/subjectcode/25-Earnings%20Releases%20and%20Operating%20Results/feedTitle/GlobeNewswire%20-%20Earnings%20Releases%20and%20Operating%20Results';

const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL || '';

interface FeedItem {
  id: string;
  title: string;
  link: string;
  published: string;
  source: 'sec' | 'globenewswire';
}

async function parseSecRss(): Promise<FeedItem[]> {
  try {
    const response = await fetch(SEC_RSS_URL, {
      headers: { 'User-Agent': 'Short Gravity Research contact@shortgravity.com' },
    });
    const text = await response.text();

    // Parse Atom feed
    const items: FeedItem[] = [];
    const entryRegex = /<entry>([\s\S]*?)<\/entry>/g;
    let match;

    while ((match = entryRegex.exec(text)) !== null) {
      const entry = match[1];
      const id = entry.match(/<id>([^<]+)<\/id>/)?.[1] || '';
      const title = entry.match(/<title>([^<]+)<\/title>/)?.[1] || '';
      const link = entry.match(/<link[^>]*href="([^"]+)"/)?.[1] || '';
      const updated = entry.match(/<updated>([^<]+)<\/updated>/)?.[1] || '';

      if (id && title) {
        items.push({
          id: id,
          title: decodeHtmlEntities(title),
          link: link,
          published: updated,
          source: 'sec',
        });
      }
    }

    return items;
  } catch (error) {
    console.error('Error parsing SEC RSS:', error);
    return [];
  }
}

async function parseGlobeNewswireRss(): Promise<FeedItem[]> {
  try {
    // GlobeNewswire feed - filter for ASTS mentions
    const response = await fetch(GLOBENEWSWIRE_RSS_URL, {
      headers: { 'User-Agent': 'Short Gravity Research' },
    });
    const text = await response.text();

    const items: FeedItem[] = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;

    while ((match = itemRegex.exec(text)) !== null) {
      const item = match[1];
      const title = item.match(/<title>([^<]+)<\/title>/)?.[1] || '';
      const link = item.match(/<link>([^<]+)<\/link>/)?.[1] || '';
      const guid = item.match(/<guid[^>]*>([^<]+)<\/guid>/)?.[1] || link;
      const pubDate = item.match(/<pubDate>([^<]+)<\/pubDate>/)?.[1] || '';

      // Only include ASTS-related items
      const titleLower = title.toLowerCase();
      if (
        titleLower.includes('ast spacemobile') ||
        titleLower.includes('asts') ||
        titleLower.includes('spacemobile')
      ) {
        items.push({
          id: guid,
          title: decodeHtmlEntities(title),
          link: link,
          published: pubDate,
          source: 'globenewswire',
        });
      }
    }

    return items;
  } catch (error) {
    console.error('Error parsing GlobeNewswire RSS:', error);
    return [];
  }
}

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'");
}

// -- Inline Embedding ---------------------------------------------------------

const CHUNK_SIZE = 2000;
const CHUNK_OVERLAP = 200;

function chunkText(text: string): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (trimmed.length <= CHUNK_SIZE) return [trimmed];

  const chunks: string[] = [];
  let start = 0;
  while (start < trimmed.length) {
    let end = start + CHUNK_SIZE;
    if (end < trimmed.length) {
      const searchStart = end - Math.floor(CHUNK_SIZE * 0.2);
      let bestBreak = -1;
      for (const sep of ['. ', '.\n', '\n\n', '; ', '\n']) {
        const pos = trimmed.lastIndexOf(sep, end);
        if (pos >= searchStart && pos + sep.length > bestBreak) {
          bestBreak = pos + sep.length;
        }
      }
      if (bestBreak > start) end = bestBreak;
    }
    const chunk = trimmed.slice(start, end).trim();
    if (chunk) chunks.push(chunk);
    start = end - CHUNK_OVERLAP;
    if (start >= trimmed.length) break;
  }
  return chunks;
}

function contentHash(text: string): string {
  return createHash('sha256').update(text).digest('hex').slice(0, 16);
}

async function embedAndStore(
  sourceId: string,
  title: string,
  fullText: string,
  dateStr: string | null,
  url: string | null,
  supabase: any,
): Promise<number> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.log('OPENAI_API_KEY not set, skipping inline embed');
    return 0;
  }

  const chunks = chunkText(fullText);
  if (chunks.length === 0) return 0;

  // Batch embed all chunks in one API call
  const embRes = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model: 'text-embedding-3-small', input: chunks }),
  });

  if (!embRes.ok) {
    console.error(`OpenAI embedding error: ${embRes.status}`);
    return 0;
  }

  const embData = await embRes.json();
  const sorted = embData.data.sort((a: any, b: any) => a.index - b.index);

  const rows = chunks.map((chunk, i) => ({
    source_table: 'press_releases',
    source_id: sourceId,
    chunk_index: i,
    title,
    chunk_text: chunk,
    content_hash: contentHash(chunk),
    metadata: { date: dateStr, url, source_label: 'PRESS RELEASE' },
    embedding: JSON.stringify(sorted[i].embedding),
  }));

  const { error } = await supabase
    .from('brain_chunks')
    .upsert(rows, { onConflict: 'source_table,source_id,chunk_index' });

  if (error) {
    console.error('brain_chunks upsert error:', error.message);
    return 0;
  }

  console.log(`Embedded ${chunks.length} chunks for ${sourceId}`);
  return chunks.length;
}

// -- Press Release Ingestion --------------------------------------------------

function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function categorizePR(title: string, content: string): { category: string; tags: string[] } {
  const t = title.toLowerCase();
  const c = (content || '').toLowerCase();

  let category = 'announcement';
  const tags: string[] = [];

  if (['launch', 'satellite', 'bluebird', 'orbit', 'bluewalker'].some((w) => t.includes(w))) {
    category = 'satellite_launch';
  } else if (['partner', 'agreement', 'at&t', 'verizon', 'vodafone'].some((w) => t.includes(w))) {
    category = 'partnership';
  } else if (['quarter', 'q1', 'q2', 'q3', 'q4', 'financial', 'results', 'earnings'].some((w) => t.includes(w))) {
    category = 'quarterly_results';
  } else if (['spectrum', 'fcc', 'license', 'authorization', 'sta '].some((w) => t.includes(w))) {
    category = 'regulatory';
  } else if (['financing', 'offering', 'capital', 'million', 'billion', 'pricing'].some((w) => t.includes(w))) {
    category = 'financing';
  } else if (['contract', 'defense', 'military', 'shield', 'dod'].some((w) => t.includes(w))) {
    category = 'defense';
  }

  for (const partner of ['at&t', 'verizon', 'vodafone', 'rakuten', 'bell', 'telus',
    'orange', 'google', 'spacex', 'blue origin', 'liberty latin']) {
    if (c.includes(partner) || t.includes(partner)) {
      tags.push(partner);
    }
  }
  if (c.includes('bluebird') || t.includes('bluebird')) tags.push('bluebird');
  if (c.includes('bluewalker') || t.includes('bluewalker')) tags.push('bluewalker');

  return { category, tags: Array.from(new Set(tags)) };
}

async function ingestPressRelease(item: FeedItem, supabase: any): Promise<boolean> {
  const sourceId = 'gnw_' + createHash('md5').update(item.id).digest('hex').slice(0, 12);

  try {
    // Fetch full article page
    const res = await fetch(item.link, {
      headers: { 'User-Agent': 'Short Gravity Research contact@shortgravity.com' },
    });
    if (!res.ok) {
      console.error(`Failed to fetch GNW page ${item.link}: ${res.status}`);
      return false;
    }

    const html = await res.text();
    const contentText = stripHtml(html).slice(0, 100000);
    const { category, tags } = categorizePR(item.title, contentText);

    const record = {
      source_id: sourceId,
      title: item.title,
      published_at: item.published ? new Date(item.published).toISOString() : new Date().toISOString(),
      url: item.link,
      category,
      tags,
      content_text: contentText,
      summary: null, // Backfilled by batch worker
      status: 'completed',
    };

    const { error } = await supabase
      .from('press_releases')
      .upsert(record, { onConflict: 'source_id' });

    if (error) {
      console.error(`Upsert error for ${sourceId}:`, error.message);
      return false;
    }

    console.log(`Ingested PR: ${sourceId} — ${item.title.slice(0, 60)}`);

    // Inline embed for immediate Brain searchability
    const dateStr = record.published_at.split('T')[0];
    await embedAndStore(sourceId, item.title, `${item.title}\n\n${contentText}`, dateStr, item.link, supabase)
      .catch((err) => console.error(`Embed error for ${sourceId}:`, err));

    return true;
  } catch (err) {
    console.error(`Error ingesting PR ${item.link}:`, err);
    return false;
  }
}

// -- Deduplication against existing tables ------------------------------------
// Replaces the feed_seen table (which doesn't exist in the schema) with
// inline checks against press_releases.source_id and filings.accession_number.

function gnwSourceId(feedId: string): string {
  return 'gnw_' + createHash('md5').update(feedId).digest('hex').slice(0, 12);
}

async function getSeenIds(supabase: any, items: FeedItem[]): Promise<Set<string>> {
  const seen = new Set<string>();

  // Check GlobeNewswire items against press_releases.source_id
  const gnwItems = items.filter(i => i.source === 'globenewswire');
  if (gnwItems.length > 0) {
    const sourceIds = gnwItems.map(i => gnwSourceId(i.id));
    try {
      const { data } = await supabase
        .from('press_releases')
        .select('source_id')
        .in('source_id', sourceIds);

      if (data) {
        const existingSourceIds = new Set(data.map((r: any) => r.source_id));
        for (const item of gnwItems) {
          if (existingSourceIds.has(gnwSourceId(item.id))) {
            seen.add(item.id);
          }
        }
      }
    } catch {
      // Non-fatal — will just re-process items
    }
  }

  // Check SEC items against filings.accession_number
  const secItems = items.filter(i => i.source === 'sec');
  if (secItems.length > 0) {
    try {
      const { data } = await supabase
        .from('filings')
        .select('accession_number, url')
        .order('filing_date', { ascending: false })
        .limit(100);

      if (data) {
        const existingUrls = new Set(data.map((r: any) => r.url));
        const existingAccessions = new Set(data.map((r: any) => r.accession_number));

        for (const item of secItems) {
          // Match by link URL or accession number extracted from link
          if (existingUrls.has(item.link)) {
            seen.add(item.id);
          } else {
            const accMatch = item.link.match(/(\d{10}-\d{2}-\d{6})/);
            if (accMatch && existingAccessions.has(accMatch[1])) {
              seen.add(item.id);
            }
          }
        }
      }
    } catch {
      // Non-fatal
    }
  }

  return seen;
}

async function sendDiscordNotification(items: FeedItem[]): Promise<void> {
  if (!DISCORD_WEBHOOK_URL || items.length === 0) return;

  for (const item of items) {
    const emoji = item.source === 'sec' ? '📄' : '📢';
    const sourceLabel = item.source === 'sec' ? 'SEC Filing' : 'Press Release';

    const embed = {
      title: `${emoji} New ${sourceLabel}`,
      description: item.title,
      url: item.link,
      color: item.source === 'sec' ? 0x0066cc : 0x00cc66,
      timestamp: new Date().toISOString(),
      footer: {
        text: 'Short Gravity Alert',
      },
    };

    try {
      await fetch(DISCORD_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ embeds: [embed] }),
      });
    } catch (error) {
      console.error('Error sending Discord notification:', error);
    }
  }
}

export const POST = createApiHandler({
  auth: 'cron',
  handler: async (request) => {
    const supabase = getServiceClient();

    // Fetch from both feeds in parallel
    const [secItems, gnwItems] = await Promise.all([
      parseSecRss(),
      parseGlobeNewswireRss(),
    ]);

    const allItems = [...secItems, ...gnwItems];
    console.log(`Fetched ${secItems.length} SEC items, ${gnwItems.length} GlobeNewswire items`);

    // Get already-seen IDs (dedup against existing tables)
    const seenIds = await getSeenIds(supabase, allItems);

    // Filter to only new items
    const newItems = allItems.filter((item) => !seenIds.has(item.id));

    let ingested = 0;

    if (newItems.length > 0) {
      console.log(`Found ${newItems.length} new items!`);

      // Send notifications (guarded — won't crash if DISCORD_WEBHOOK_URL is not set)
      await sendDiscordNotification(newItems);

      // Ingest new GNW press releases into press_releases table
      const gnwNew = newItems.filter((i) => i.source === 'globenewswire');
      for (const item of gnwNew) {
        const ok = await ingestPressRelease(item, supabase);
        if (ok) ingested++;
      }
    }

    return NextResponse.json({
      success: true,
      checked: {
        sec: secItems.length,
        globenewswire: gnwItems.length,
      },
      newItems: newItems.length,
      ingested,
      items: newItems.map((i) => ({ source: i.source, title: i.title })),
    });
  },
})

// Also support GET for manual testing
export const GET = POST
