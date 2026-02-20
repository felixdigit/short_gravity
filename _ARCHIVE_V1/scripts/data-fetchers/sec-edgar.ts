/**
 * SEC EDGAR Data Fetcher for ASTS
 * Fetches filings from SEC's free API
 *
 * CIK: 0001780312 (AST SpaceMobile)
 * API Docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
 */

const ASTS_CIK = "0001780312";
const SEC_BASE_URL = "https://data.sec.gov";
const USER_AGENT = "Short Gravity gabriel@shortgravity.com"; // SEC requires identification

interface SECFiling {
  accessionNumber: string;
  filingDate: string;
  reportDate: string;
  form: string;
  primaryDocument: string;
  primaryDocDescription: string;
  items?: string;
  size: number;
  isXBRL: boolean;
  isInlineXBRL: boolean;
}

interface SECSubmissions {
  cik: string;
  entityType: string;
  sic: string;
  sicDescription: string;
  name: string;
  tickers: string[];
  exchanges: string[];
  filings: {
    recent: {
      accessionNumber: string[];
      filingDate: string[];
      reportDate: string[];
      form: string[];
      primaryDocument: string[];
      primaryDocDescription: string[];
      items: string[];
      size: number[];
      isXBRL: number[];
      isInlineXBRL: number[];
    };
  };
}

async function fetchWithRetry(url: string, retries = 3): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        headers: {
          "User-Agent": USER_AGENT,
          "Accept": "application/json",
        },
      });

      if (response.status === 429) {
        // Rate limited - wait and retry
        const waitTime = Math.pow(2, i) * 1000;
        console.log(`Rate limited. Waiting ${waitTime}ms...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  throw new Error("Max retries exceeded");
}

export async function fetchASTSSubmissions(): Promise<SECSubmissions> {
  const url = `${SEC_BASE_URL}/submissions/CIK${ASTS_CIK}.json`;
  console.log(`Fetching: ${url}`);

  const response = await fetchWithRetry(url);
  return response.json();
}

export function parseFilings(submissions: SECSubmissions): SECFiling[] {
  const recent = submissions.filings.recent;
  const filings: SECFiling[] = [];

  for (let i = 0; i < recent.accessionNumber.length; i++) {
    filings.push({
      accessionNumber: recent.accessionNumber[i],
      filingDate: recent.filingDate[i],
      reportDate: recent.reportDate[i],
      form: recent.form[i],
      primaryDocument: recent.primaryDocument[i],
      primaryDocDescription: recent.primaryDocDescription[i],
      items: recent.items[i],
      size: recent.size[i],
      isXBRL: recent.isXBRL[i] === 1,
      isInlineXBRL: recent.isInlineXBRL[i] === 1,
    });
  }

  return filings;
}

export function filterByFormType(filings: SECFiling[], formTypes: string[]): SECFiling[] {
  return filings.filter(f => formTypes.includes(f.form));
}

export function getFilingUrl(cik: string, accessionNumber: string, document: string): string {
  const accessionNoDashes = accessionNumber.replace(/-/g, "");
  return `https://www.sec.gov/Archives/edgar/data/${cik}/${accessionNoDashes}/${document}`;
}

export async function fetchFilingDocument(filing: SECFiling): Promise<string> {
  const url = getFilingUrl(ASTS_CIK, filing.accessionNumber, filing.primaryDocument);
  console.log(`Fetching document: ${url}`);

  const response = await fetchWithRetry(url);
  return response.text();
}

// Key form types for ASTS analysis
export const FORM_TYPES = {
  ANNUAL: ["10-K", "10-K/A"],
  QUARTERLY: ["10-Q", "10-Q/A"],
  CURRENT: ["8-K", "8-K/A"],
  PROXY: ["DEF 14A", "DEFA14A"],
  REGISTRATION: ["S-1", "S-1/A", "S-3", "S-3/A"],
  INSIDER: ["4", "3", "5"],
  PROSPECTUS: ["424B3", "424B4", "424B5"],
};

// Main execution
async function main() {
  console.log("=== SEC EDGAR Fetcher for ASTS ===\n");

  try {
    // Fetch all submissions
    const submissions = await fetchASTSSubmissions();
    console.log(`Company: ${submissions.name}`);
    console.log(`CIK: ${submissions.cik}`);
    console.log(`Tickers: ${submissions.tickers.join(", ")}`);
    console.log(`Exchanges: ${submissions.exchanges.join(", ")}`);
    console.log(`Industry: ${submissions.sicDescription}\n`);

    // Parse filings
    const allFilings = parseFilings(submissions);
    console.log(`Total filings: ${allFilings.length}\n`);

    // Filter key filings
    const keyForms = [...FORM_TYPES.ANNUAL, ...FORM_TYPES.QUARTERLY, ...FORM_TYPES.CURRENT];
    const keyFilings = filterByFormType(allFilings, keyForms);

    console.log("=== Key Filings (10-K, 10-Q, 8-K) ===\n");

    // Group by year
    const byYear = new Map<string, SECFiling[]>();
    for (const filing of keyFilings) {
      const year = filing.filingDate.slice(0, 4);
      if (!byYear.has(year)) byYear.set(year, []);
      byYear.get(year)!.push(filing);
    }

    // Print summary
    for (const [year, filings] of [...byYear.entries()].sort().reverse()) {
      console.log(`\n${year}:`);
      for (const f of filings.slice(0, 10)) {
        const url = getFilingUrl(ASTS_CIK, f.accessionNumber, f.primaryDocument);
        console.log(`  ${f.filingDate} | ${f.form.padEnd(8)} | ${f.primaryDocDescription.slice(0, 50)}`);
      }
      if (filings.length > 10) {
        console.log(`  ... and ${filings.length - 10} more`);
      }
    }

    // Output JSON for storage
    const output = {
      fetchedAt: new Date().toISOString(),
      company: {
        name: submissions.name,
        cik: submissions.cik,
        tickers: submissions.tickers,
        exchanges: submissions.exchanges,
        industry: submissions.sicDescription,
      },
      filings: keyFilings.map(f => ({
        ...f,
        url: getFilingUrl(ASTS_CIK, f.accessionNumber, f.primaryDocument),
      })),
    };

    // Write to research folder
    const fs = await import("fs/promises");
    const outputPath = "../../research/asts/filings/sec-filings.json";
    await fs.writeFile(outputPath, JSON.stringify(output, null, 2));
    console.log(`\n\nSaved to: ${outputPath}`);

  } catch (error) {
    console.error("Error:", error);
    process.exit(1);
  }
}

// Run if executed directly
main();
