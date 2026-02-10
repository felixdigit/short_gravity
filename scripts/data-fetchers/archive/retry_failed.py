#!/usr/bin/env python3
"""
Retry failed filings - generates AI summaries for filings that previously failed.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
ASTS_CIK = "0001780312"
USER_AGENT = "Short Gravity Research gabriel@shortgravity.com"

ITEM_CODES = {
    "1.01": "Entry into Material Agreement",
    "1.02": "Termination of Material Agreement",
    "2.01": "Completion of Acquisition/Disposition",
    "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of Direct Financial Obligation",
    "3.02": "Unregistered Sales of Equity Securities",
    "5.02": "Departure/Appointment of Directors or Officers",
    "5.07": "Submission of Matters to Vote",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fetch_url(url: str, headers: Optional[Dict] = None) -> str:
    default_headers = {"User-Agent": USER_AGENT}
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read()
        # Try UTF-8 first, fall back to latin-1 for SEC files with special chars
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")


def extract_text_from_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Remove null bytes and other problematic characters for Postgres
    text = text.replace("\x00", "").replace("\u0000", "")
    return text


def get_item_descriptions(items: str) -> List[str]:
    if not items:
        return []
    return [ITEM_CODES.get(item.strip(), f"Item {item.strip()}") for item in items.split(",")]


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
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
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_failed_filings() -> List[Dict]:
    result = supabase_request("GET", "filings?status=eq.failed&select=*")
    return result


def update_filing(accession_number: str, updates: Dict) -> Dict:
    endpoint = f"filings?accession_number=eq.{accession_number}"
    return supabase_request("PATCH", endpoint, updates)


def generate_summary(content: str, form: str, items: str) -> str:
    item_descriptions = get_item_descriptions(items)
    items_context = ""
    if item_descriptions:
        items_context = f"\n\nItems reported: {', '.join(item_descriptions)}"

    max_content = 50000
    truncated = content[:max_content] if len(content) > max_content else content

    prompt = f"""You are analyzing an SEC {form} filing for AST SpaceMobile (ASTS), a company building a space-based cellular network.{items_context}

Provide a concise summary (2-4 sentences) of the key information in this filing that would be most relevant to investors. Focus on:
- Material business developments
- Financial metrics or guidance
- Partnership/contract updates
- Satellite launch or operational milestones
- Executive changes
- Any risks or concerns

Filing content:
{truncated}

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    log("Calling Claude API for summary...")

    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["content"][0]["text"].strip()


def process_failed_filing(filing: Dict) -> bool:
    accession = filing["accession_number"]
    log(f"Retrying {filing['form']} filed {filing['filing_date']}: {accession}")

    try:
        # Update status to processing
        update_filing(accession, {"status": "processing", "error_message": None})

        # Fetch content if not already present
        content = filing.get("content_text")
        if not content:
            log(f"  Fetching content from SEC...")
            html = fetch_url(filing["url"])
            content = extract_text_from_html(html)

        content_length = len(content)
        log(f"  Content length: {content_length:,} chars")

        # Generate summary
        summary = generate_summary(content, filing["form"], filing.get("items", "") or "")
        log(f"  Summary: {summary[:100]}...")

        # Update with content and summary
        update_filing(accession, {
            "content_text": content[:100000],
            "content_length": content_length,
            "summary": summary,
            "summary_model": "claude-sonnet-4-20250514",
            "summary_generated_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
        })

        log(f"  ✓ Completed")
        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        update_filing(accession, {
            "status": "failed",
            "error_message": str(e)[:500],
        })
        return False


def main():
    log("=" * 60)
    log("Retry Failed Filings")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        log("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    failed = get_failed_filings()
    log(f"Found {len(failed)} failed filings to retry")

    if not failed:
        log("No failed filings. Done.")
        return

    success = 0
    failed_count = 0

    for filing in failed:
        if process_failed_filing(filing):
            success += 1
        else:
            failed_count += 1
        # Longer delay to avoid rate limits
        time.sleep(5)

    log("=" * 60)
    log(f"Completed: {success} success, {failed_count} failed")
    log("=" * 60)


if __name__ == "__main__":
    main()
