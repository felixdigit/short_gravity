/**
 * API Route: Sync SEC filings from EDGAR
 * POST /api/cron/filings-sync
 *
 * Fetches new ASTS filings from SEC EDGAR, extracts content,
 * and stores them in Supabase.
 * Called by Vercel cron every 15 minutes.
 */

import { NextResponse } from 'next/server';
import { createApiHandler } from '@/lib/api/handler';
import { getServiceClient } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const maxDuration = 60; // Vercel Pro caps at 60s — 5 filings × 2s rate limit = ~20-30s total

// Configuration
const ASTS_CIK = '0001780312';
const SEC_BASE_URL = 'https://data.sec.gov';
const SEC_ARCHIVES_URL = 'https://www.sec.gov/Archives/edgar/data';
const USER_AGENT = 'Short Gravity Research gabriel@shortgravity.com';

// High-signal forms for frontend filtering
const HIGH_SIGNAL_FORMS = ['10-K', '10-K/A', '10-Q', '10-Q/A', '8-K', '8-K/A'];

interface SECFiling {
  accession_number: string;
  form: string;
  filing_date: string;
  report_date: string | null;
  primary_document: string;
  primary_doc_description: string | null;
  items: string;
  file_size: number;
  url: string;
  is_high_signal: boolean;
}

interface SECSubmissionsResponse {
  filings: {
    recent: {
      accessionNumber: string[];
      form: string[];
      filingDate: string[];
      reportDate: (string | null)[];
      primaryDocument: string[];
      primaryDocDescription: (string | null)[];
      items?: string[];
      size: number[];
    };
  };
}

function getFilingUrl(accessionNumber: string, document: string): string {
  const accessionNoDashes = accessionNumber.replace(/-/g, '');
  return `${SEC_ARCHIVES_URL}/${ASTS_CIK}/${accessionNoDashes}/${document}`;
}

function extractTextFromHtml(html: string): string {
  // Remove script and style tags
  let text = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
  text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');

  // Remove HTML tags
  text = text.replace(/<[^>]+>/g, ' ');

  // Decode common HTML entities
  text = text.replace(/&nbsp;/g, ' ');
  text = text.replace(/&amp;/g, '&');
  text = text.replace(/&lt;/g, '<');
  text = text.replace(/&gt;/g, '>');
  text = text.replace(/&quot;/g, '"');
  text = text.replace(/&#\d+;/g, '');

  // Clean up whitespace
  text = text.replace(/\s+/g, ' ').trim();

  return text;
}

async function fetchRecentFilings(limit: number = 100): Promise<SECFiling[]> {
  const url = `${SEC_BASE_URL}/submissions/CIK${ASTS_CIK}.json`;
  console.log(`[Filings] Fetching SEC submissions: ${url}`);

  const response = await fetch(url, {
    headers: {
      'User-Agent': USER_AGENT,
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`SEC API error: ${response.status}`);
  }

  const data = (await response.json()) as SECSubmissionsResponse;
  const recent = data.filings.recent;
  const filings: SECFiling[] = [];

  const totalFilings = recent.accessionNumber.length;
  for (let i = 0; i < totalFilings && filings.length < limit; i++) {
    const form = recent.form[i];
    const isHighSignal = HIGH_SIGNAL_FORMS.includes(form);

    filings.push({
      accession_number: recent.accessionNumber[i],
      form,
      filing_date: recent.filingDate[i],
      report_date: recent.reportDate[i] || null,
      primary_document: recent.primaryDocument[i],
      primary_doc_description: recent.primaryDocDescription[i] || null,
      items: recent.items?.[i] || '',
      file_size: recent.size[i],
      url: getFilingUrl(recent.accessionNumber[i], recent.primaryDocument[i]),
      is_high_signal: isHighSignal,
    });
  }

  return filings;
}

async function fetchFilingContent(url: string): Promise<string> {
  console.log(`[Filings] Fetching content: ${url}`);

  const response = await fetch(url, {
    headers: { 'User-Agent': USER_AGENT },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch filing: ${response.status}`);
  }

  const html = await response.text();
  return extractTextFromHtml(html);
}

export const POST = createApiHandler({
  auth: 'cron',
  handler: async () => {
    const startTime = Date.now();
    const supabase = getServiceClient();

    // Get recent accession numbers — only check filings from last 90 days
    const ninetyDaysAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    const { data: existingFilings, error: fetchError } = await supabase
      .from('filings')
      .select('accession_number')
      .gte('filing_date', ninetyDaysAgo)
      .order('filing_date', { ascending: false })
      .limit(200);

    if (fetchError) {
      console.error('[Filings] Error fetching existing filings:', fetchError);
    }

    const existingAccessions = new Set(
      (existingFilings || []).map((f) => f.accession_number)
    );
    console.log(`[Filings] Found ${existingAccessions.size} existing filings in database`);

    // Fetch recent filings from SEC
    const recentFilings = await fetchRecentFilings(100);
    console.log(`[Filings] Fetched ${recentFilings.length} recent filings from SEC`);

    // Find new filings
    const newFilings = recentFilings.filter(
      (f) => !existingAccessions.has(f.accession_number)
    );
    console.log(`[Filings] New filings to process: ${newFilings.length}`);

    if (newFilings.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No new filings',
        existingCount: existingAccessions.size,
        timestamp: new Date().toISOString(),
      });
    }

    // Process new filings (limit to 5 per run to stay within timeout)
    const maxToProcess = 5;
    const toProcess = newFilings.slice(0, maxToProcess);
    const results: { accession: string; form: string; success: boolean; error?: string }[] = [];

    for (const filing of toProcess) {
      const accession = filing.accession_number;
      const form = filing.form;
      console.log(`[Filings] Processing ${form} filed ${filing.filing_date}: ${accession}`);

      try {
        // Insert with processing status
        const { error: insertError } = await supabase.from('filings').insert({
          accession_number: accession,
          form,
          filing_date: filing.filing_date,
          report_date: filing.report_date,
          primary_document: filing.primary_document,
          primary_doc_description: filing.primary_doc_description,
          items: filing.items,
          url: filing.url,
          is_high_signal: filing.is_high_signal,
          status: 'processing',
        });

        if (insertError) {
          throw new Error(`Insert error: ${insertError.message}`);
        }

        // Fetch content
        const content = await fetchFilingContent(filing.url);
        const contentLength = content.length;
        console.log(`[Filings] Content length: ${contentLength.toLocaleString()} chars`);

        // Skip AI summaries in cron - run manually via filing_worker.py
        const summary = null;
        const summaryModel = null;

        // Update with content and mark completed
        const { error: updateError } = await supabase
          .from('filings')
          .update({
            content_text: content,
            content_length: contentLength,
            summary,
            summary_model: summaryModel,
            summary_generated_at: summary ? new Date().toISOString() : null,
            status: 'completed',
          })
          .eq('accession_number', accession);

        if (updateError) {
          throw new Error(`Update error: ${updateError.message}`);
        }

        console.log(`[Filings] Completed: ${accession}`);
        results.push({ accession, form, success: true });

        // Rate limit: 2-second delay between individual filing fetches
        await new Promise((resolve) => setTimeout(resolve, 2000));
      } catch (error) {
        console.error(`[Filings] Error processing ${accession}:`, error);

        // Mark as failed
        await supabase
          .from('filings')
          .update({
            status: 'failed',
            error_message: error instanceof Error ? error.message : String(error),
          })
          .eq('accession_number', accession);

        results.push({
          accession,
          form,
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    const duration = Date.now() - startTime;
    const successCount = results.filter((r) => r.success).length;
    const failCount = results.filter((r) => !r.success).length;

    console.log(`[Filings] Sync complete: ${successCount} success, ${failCount} failed, ${duration}ms`);

    return NextResponse.json({
      success: true,
      processed: results.length,
      successCount,
      failCount,
      remaining: newFilings.length - toProcess.length,
      duration,
      results,
      timestamp: new Date().toISOString(),
    });
  },
})

// Also support GET for manual testing
export const GET = POST;
