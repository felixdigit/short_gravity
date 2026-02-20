#!/usr/bin/env python3
"""
Glossary Extraction Worker

Extracts key terms from ASTS filings using Claude API,
deduplicates, and stores in Supabase glossary tables.

Run: python3 glossary_worker.py
     python3 glossary_worker.py --dry-run
     python3 glossary_worker.py --filing <accession_number>
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Categories
CATEGORIES = ["financial", "technical", "regulatory", "company", "partnership", "acronym"]

# Extraction prompt
EXTRACTION_PROMPT = """You are analyzing an {agency} {form_type} filing for AST SpaceMobile (ASTS), a company building a space-based cellular broadband network using satellites to connect directly to standard mobile phones.

Extract key terms that would be valuable in a glossary for investors and researchers fact-checking information about the company. For each term:

1. **term**: The canonical name (proper capitalization)
2. **category**: One of: financial, technical, regulatory, company, partnership, acronym
3. **definition**: 1-3 sentence explanation in context of ASTS (be specific, not generic)
4. **excerpt**: The exact passage where this term appears (200-400 chars, include enough context)
5. **importance**: low, normal, high, or critical (critical = core business metrics/technology)

Categories:
- **financial**: Revenue metrics, subscriber numbers, ARPU, contract values, financial guidance
- **technical**: Satellite specs, orbital parameters, spectrum bands, antenna technology, network architecture
- **regulatory**: FCC filings, ITU coordination, spectrum licenses, regulatory approvals
- **company**: ASTS-specific terms (BlueBird, BlueWalker, product names, internal terminology)
- **partnership**: MNO partners, commercial agreements, specific carrier names
- **acronym**: Industry abbreviations with full definitions (LEO, TLE, D2D, etc.)

Rules:
- Skip generic business terms (revenue, CEO, quarterly) unless ASTS-specific
- Include technical specifications with actual numbers when present
- For acronyms, always provide the full expansion
- Excerpts must be verbatim from the filing
- Focus on terms SpaceMob community would want to verify

Return a JSON array of objects. If no valuable terms found, return empty array [].

Filing content:
{content}"""


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def normalize_term(term: str) -> str:
    """Normalize term for deduplication."""
    # Lowercase, remove punctuation, collapse whitespace
    normalized = term.lower().strip()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


# ============================================================================
# SUPABASE
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Any:
    """Make Supabase REST API request."""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY not set")

    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_sec_filings(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Get SEC filings with content."""
    endpoint = f"filings?select=accession_number,form,filing_date,content_text&status=eq.completed&order=filing_date.desc&limit={limit}&offset={offset}"
    return supabase_request("GET", endpoint)


def get_fcc_filings(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Get FCC filings with content."""
    endpoint = f"fcc_filings?select=file_number,filing_type,filed_date,content_text,title&status=eq.completed&order=filed_date.desc&limit={limit}&offset={offset}"
    return supabase_request("GET", endpoint)


def get_existing_terms() -> Dict[str, str]:
    """Get normalized terms already in glossary. Returns {normalized_term: id}."""
    try:
        result = supabase_request("GET", "glossary_terms?select=id,normalized_term")
        return {r["normalized_term"]: r["id"] for r in result}
    except Exception as e:
        log(f"Error fetching existing terms: {e}")
        return {}


def insert_term(term_data: Dict) -> Optional[str]:
    """Insert new glossary term. Returns term ID."""
    try:
        result = supabase_request("POST", "glossary_terms", term_data)
        if result and len(result) > 0:
            return result[0]["id"]
    except urllib.error.HTTPError as e:
        if e.code == 409:  # Conflict - term already exists
            log(f"  Term already exists: {term_data['term']}")
        else:
            raise
    return None


def insert_citation(citation_data: Dict) -> bool:
    """Insert glossary citation."""
    try:
        supabase_request("POST", "glossary_citations", citation_data)
        return True
    except Exception as e:
        log(f"  Citation insert error: {e}")
        return False


def update_term_mention_count(term_id: str, increment: int = 1) -> bool:
    """Increment mention count for a term."""
    try:
        # Get current count
        result = supabase_request("GET", f"glossary_terms?id=eq.{term_id}&select=mention_count")
        if result:
            current = result[0].get("mention_count", 0) or 0
            supabase_request("PATCH", f"glossary_terms?id=eq.{term_id}", {
                "mention_count": current + increment
            })
            return True
    except Exception as e:
        log(f"  Mention count update error: {e}")
    return False


def check_citation_exists(term_id: str, sec_accession: Optional[str], fcc_file: Optional[str]) -> bool:
    """Check if citation already exists."""
    try:
        if sec_accession:
            endpoint = f"glossary_citations?term_id=eq.{term_id}&sec_accession_number=eq.{sec_accession}&select=id"
        else:
            endpoint = f"glossary_citations?term_id=eq.{term_id}&fcc_file_number=eq.{fcc_file}&select=id"
        result = supabase_request("GET", endpoint)
        return len(result) > 0
    except:
        return False


# ============================================================================
# CLAUDE API
# ============================================================================

def extract_terms_from_content(content: str, agency: str, form_type: str) -> List[Dict]:
    """Call Claude to extract terms from filing content."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    # Truncate content if too long (keep first 80K chars for context)
    max_content = 80000
    truncated = content[:max_content] if len(content) > max_content else content

    prompt = EXTRACTION_PROMPT.format(
        agency=agency,
        form_type=form_type,
        content=truncated
    )

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            text = result["content"][0]["text"].strip()

            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            terms = json.loads(text)
            return terms if isinstance(terms, list) else []
    except json.JSONDecodeError as e:
        log(f"  JSON parse error: {e}")
        return []
    except Exception as e:
        log(f"  Claude API error: {e}")
        return []


# ============================================================================
# PROCESSING
# ============================================================================

def process_sec_filing(filing: Dict, existing_terms: Dict[str, str], dry_run: bool = False) -> Tuple[int, int]:
    """Process a single SEC filing. Returns (new_terms, new_citations)."""
    accession = filing["accession_number"]
    form = filing["form"]
    filing_date = filing["filing_date"]
    content = filing.get("content_text", "")

    if not content or len(content) < 500:
        log(f"  Skipping {accession}: insufficient content")
        return 0, 0

    log(f"Processing SEC {form} ({filing_date}): {accession}")
    log(f"  Content: {len(content):,} chars")

    # Extract terms
    terms = extract_terms_from_content(content, "SEC", form)
    log(f"  Extracted: {len(terms)} terms")

    new_terms = 0
    new_citations = 0

    for term_data in terms:
        term = term_data.get("term", "").strip()
        if not term:
            continue

        normalized = normalize_term(term)
        category = term_data.get("category", "").lower()
        if category not in CATEGORIES:
            category = "company"  # Default

        definition = term_data.get("definition", "").strip()
        excerpt = term_data.get("excerpt", "").strip()[:500]
        importance = term_data.get("importance", "normal").lower()
        if importance not in ["low", "normal", "high", "critical"]:
            importance = "normal"

        if dry_run:
            log(f"    [DRY] Term: {term} ({category})")
            new_terms += 1
            continue

        # Check if term exists
        term_id = existing_terms.get(normalized)

        if not term_id:
            # Insert new term
            term_record = {
                "term": term,
                "normalized_term": normalized,
                "definition": definition,
                "category": category,
                "importance": importance,
                "first_seen_date": filing_date,
                "mention_count": 1,
                "status": "draft",
            }
            term_id = insert_term(term_record)
            if term_id:
                existing_terms[normalized] = term_id
                new_terms += 1
                log(f"    + New term: {term}")
        else:
            # Update mention count
            update_term_mention_count(term_id)

        # Add citation if we have term_id and excerpt
        if term_id and excerpt:
            if not check_citation_exists(term_id, accession, None):
                citation = {
                    "term_id": term_id,
                    "sec_accession_number": accession,
                    "excerpt": excerpt,
                    "filing_date": filing_date,
                    "filing_type": form,
                    "is_primary": new_terms > 0,  # Primary if this is where term was first seen
                }
                if insert_citation(citation):
                    new_citations += 1

    return new_terms, new_citations


def process_fcc_filing(filing: Dict, existing_terms: Dict[str, str], dry_run: bool = False) -> Tuple[int, int]:
    """Process a single FCC filing. Returns (new_terms, new_citations)."""
    file_number = filing["file_number"]
    filing_type = filing.get("filing_type", "Application")
    filed_date = filing["filed_date"]
    content = filing.get("content_text", "")
    title = filing.get("title", "")

    # Use title + content
    full_content = f"{title}\n\n{content}" if title else content

    if not full_content or len(full_content) < 200:
        log(f"  Skipping {file_number}: insufficient content")
        return 0, 0

    log(f"Processing FCC {filing_type} ({filed_date}): {file_number}")
    log(f"  Content: {len(full_content):,} chars")

    # Extract terms
    terms = extract_terms_from_content(full_content, "FCC", filing_type)
    log(f"  Extracted: {len(terms)} terms")

    new_terms = 0
    new_citations = 0

    for term_data in terms:
        term = term_data.get("term", "").strip()
        if not term:
            continue

        normalized = normalize_term(term)
        category = term_data.get("category", "").lower()
        if category not in CATEGORIES:
            category = "regulatory"  # Default for FCC

        definition = term_data.get("definition", "").strip()
        excerpt = term_data.get("excerpt", "").strip()[:500]
        importance = term_data.get("importance", "normal").lower()
        if importance not in ["low", "normal", "high", "critical"]:
            importance = "normal"

        if dry_run:
            log(f"    [DRY] Term: {term} ({category})")
            new_terms += 1
            continue

        # Check if term exists
        term_id = existing_terms.get(normalized)

        if not term_id:
            # Insert new term
            term_record = {
                "term": term,
                "normalized_term": normalized,
                "definition": definition,
                "category": category,
                "importance": importance,
                "first_seen_date": filed_date,
                "mention_count": 1,
                "status": "draft",
            }
            term_id = insert_term(term_record)
            if term_id:
                existing_terms[normalized] = term_id
                new_terms += 1
                log(f"    + New term: {term}")
        else:
            # Update mention count
            update_term_mention_count(term_id)

        # Add citation
        if term_id and excerpt:
            if not check_citation_exists(term_id, None, file_number):
                citation = {
                    "term_id": term_id,
                    "fcc_file_number": file_number,
                    "excerpt": excerpt,
                    "filing_date": filed_date,
                    "filing_type": filing_type,
                    "is_primary": new_terms > 0,
                }
                if insert_citation(citation):
                    new_citations += 1

    return new_terms, new_citations


def run_extraction(dry_run: bool = False, specific_filing: Optional[str] = None):
    """Main extraction loop."""
    log("=" * 60)
    log("Glossary Extraction Worker")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        log("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    if dry_run:
        log("DRY RUN MODE - no changes will be made")

    # Get existing terms
    existing_terms = get_existing_terms() if not dry_run else {}
    log(f"Existing glossary terms: {len(existing_terms)}")

    total_new_terms = 0
    total_new_citations = 0

    # Process specific filing if requested
    if specific_filing:
        log(f"Processing specific filing: {specific_filing}")
        if "-" in specific_filing and len(specific_filing) > 15:
            # SEC accession number format
            filings = supabase_request("GET", f"filings?accession_number=eq.{specific_filing}&select=accession_number,form,filing_date,content_text")
            if filings:
                new_t, new_c = process_sec_filing(filings[0], existing_terms, dry_run)
                total_new_terms += new_t
                total_new_citations += new_c
        else:
            # FCC file number
            filings = supabase_request("GET", f"fcc_filings?file_number=eq.{specific_filing}&select=file_number,filing_type,filed_date,content_text,title")
            if filings:
                new_t, new_c = process_fcc_filing(filings[0], existing_terms, dry_run)
                total_new_terms += new_t
                total_new_citations += new_c
    else:
        # Process high-signal SEC filings first (10-K, 10-Q, 8-K)
        log("\n--- Processing SEC Filings ---")
        high_signal_forms = ["10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"]

        for form in high_signal_forms:
            log(f"\nFetching {form} filings...")
            sec_filings = supabase_request(
                "GET",
                f"filings?select=accession_number,form,filing_date,content_text&status=eq.completed&form=eq.{form}&order=filing_date.desc&limit=50"
            )
            log(f"Found {len(sec_filings)} {form} filings")

            for filing in sec_filings:
                new_t, new_c = process_sec_filing(filing, existing_terms, dry_run)
                total_new_terms += new_t
                total_new_citations += new_c
                time.sleep(1)  # Rate limit

        # Process FCC filings
        log("\n--- Processing FCC Filings ---")
        offset = 0
        batch_size = 50

        while True:
            fcc_filings = get_fcc_filings(limit=batch_size, offset=offset)
            if not fcc_filings:
                break

            log(f"Processing FCC batch {offset}-{offset+len(fcc_filings)}")

            for filing in fcc_filings:
                new_t, new_c = process_fcc_filing(filing, existing_terms, dry_run)
                total_new_terms += new_t
                total_new_citations += new_c
                time.sleep(1)  # Rate limit

            offset += batch_size

            # Limit total FCC filings for initial run
            if offset >= 200:
                log("Reached FCC limit for this run")
                break

    log("\n" + "=" * 60)
    log(f"Extraction Complete")
    log(f"  New terms: {total_new_terms}")
    log(f"  New citations: {total_new_citations}")
    log("=" * 60)


def publish_terms():
    """Publish all draft terms (after manual review)."""
    log("Publishing draft terms...")
    try:
        result = supabase_request("PATCH", "glossary_terms?status=eq.draft", {"status": "published"})
        log(f"Published {len(result) if result else 0} terms")
    except Exception as e:
        log(f"Error publishing: {e}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    specific_filing = None

    if "--filing" in sys.argv:
        idx = sys.argv.index("--filing")
        if idx + 1 < len(sys.argv):
            specific_filing = sys.argv[idx + 1]

    if "--publish" in sys.argv:
        publish_terms()
    else:
        run_extraction(dry_run=dry_run, specific_filing=specific_filing)
