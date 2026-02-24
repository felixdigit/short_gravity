#!/usr/bin/env python3
"""
Embedding Worker — Chunk and embed all documents for Brain hybrid search.

Reads from patents, patent_claims, filings, fcc_filings, press_releases, earnings_transcripts.
Chunks text into ~500-token segments.
Embeds via OpenAI text-embedding-3-small (1536 dims).
Upserts into brain_chunks table for vector search.

Usage:
    python3 embedding_worker.py                # Incremental (skip existing)
    python3 embedding_worker.py --force        # Re-embed everything
    python3 embedding_worker.py --table patents # Single table only
    python3 embedding_worker.py --dry-run      # Preview without writing

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY — Database
    OPENAI_API_KEY — For embeddings

Cost estimate: ~4,000 documents × ~3 chunks avg × ~500 tokens = ~6M tokens
    text-embedding-3-small: $0.02/1M tokens → ~$0.12 total
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536

# Chunking: ~500 tokens ≈ 2000 chars, with 200 char overlap
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200

# OpenAI batch limits
EMBED_BATCH_SIZE = 50  # texts per API call (max 2048, but stay conservative)
EMBED_DELAY = 0.5      # seconds between batches

# Supabase upsert batch
UPSERT_BATCH_SIZE = 100


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# =============================================================================
# HTTP UTILITIES (matches patent_worker_v2.py pattern)
# =============================================================================

def http_request(url: str, method: str = "GET", headers: Dict = None,
                 data: Any = None, timeout: int = 60) -> bytes:
    headers = headers or {}
    body = None
    if data:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode()
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            body = data.encode()
        else:
            body = data

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_json(url: str, method: str = "GET", headers: Dict = None,
              data: Any = None) -> Any:
    resp = http_request(url, method, headers, data)
    return json.loads(resp.decode())


# =============================================================================
# SUPABASE
# =============================================================================

def supabase_headers() -> Dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def supabase_get(endpoint: str) -> List[Dict]:
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    try:
        resp = http_request(url, "GET", supabase_headers())
        return json.loads(resp.decode())
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        log(f"  Supabase GET error {e.code}: {error[:200]}")
        return []


def supabase_paginate(endpoint: str, page_size: int = 1000) -> List[Dict]:
    """Paginate through all results."""
    all_results = []
    offset = 0
    while True:
        sep = "&" if "?" in endpoint else "?"
        page = supabase_get(f"{endpoint}{sep}limit={page_size}&offset={offset}")
        if not page:
            break
        all_results.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return all_results


def supabase_upsert(table: str, rows: List[Dict],
                    on_conflict: str = None) -> int:
    """Upsert rows into a table. Returns count of rows upserted."""
    if not rows:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if on_conflict:
        url += f"?on_conflict={on_conflict}"
    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    count = 0
    for i in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[i:i + UPSERT_BATCH_SIZE]
        try:
            http_request(url, "POST", headers, batch)
            count += len(batch)
        except urllib.error.HTTPError as e:
            error = e.read().decode() if e.fp else ""
            log(f"  Upsert error {e.code}: {error[:300]}")
    return count


# =============================================================================
# OPENAI EMBEDDINGS
# =============================================================================

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings for a batch of texts from OpenAI."""
    if not texts:
        return []

    resp = http_json(
        "https://api.openai.com/v1/embeddings",
        method="POST",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        data={
            "model": EMBEDDING_MODEL,
            "input": texts,
        },
    )

    # Sort by index to maintain order
    sorted_data = sorted(resp["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_data]


# =============================================================================
# CHUNKING
# =============================================================================

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS,
               overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if not text or not text.strip():
        return []

    text = text.strip()

    # Short text = single chunk
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 20% of chunk
            search_start = end - int(chunk_size * 0.2)
            best_break = -1
            for sep in [". ", ".\n", "\n\n", "; ", "\n"]:
                pos = text.rfind(sep, search_start, end)
                if pos > best_break:
                    best_break = pos + len(sep)

            if best_break > start:
                end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# =============================================================================
# SOURCE EXTRACTORS
# =============================================================================

def extract_patents(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from patents table."""
    log("Fetching patents...")
    rows = supabase_paginate(
        "patents?select=patent_number,title,abstract,content_text,grant_date,source_url,family_id"
    )
    log(f"  Found {len(rows)} patents")

    chunks = []
    for row in rows:
        patent_number = row.get("patent_number", "")
        title = row.get("title", "")
        text = row.get("content_text") or row.get("abstract") or ""

        if not text.strip():
            continue

        # Prepend title to content for context
        full_text = f"{title}\n\n{text}" if title else text
        text_chunks = chunk_text(full_text)

        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "patents",
                "source_id": patent_number,
                "chunk_index": i,
                "title": title,
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "date": row.get("grant_date"),
                    "url": row.get("source_url"),
                    "source_label": "PATENT",
                    "family_id": row.get("family_id"),
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


def extract_patent_claims(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from patent_claims table. Each claim = 1 chunk."""
    log("Fetching patent claims...")
    rows = supabase_paginate(
        "patent_claims?select=id,patent_number,claim_number,claim_text,claim_type"
    )
    log(f"  Found {len(rows)} claims")

    # Build patent_number → family_id lookup
    patent_families = supabase_paginate(
        "patents?select=patent_number,family_id&family_id=not.is.null"
    )
    family_map = {p["patent_number"]: p["family_id"] for p in patent_families}
    log(f"  Loaded {len(family_map)} patent→family mappings")

    chunks = []
    for row in rows:
        claim_text = row.get("claim_text", "").strip()
        if not claim_text:
            continue

        patent_number = row.get("patent_number", "")
        claim_number = row.get("claim_number", 0)
        claim_type = row.get("claim_type", "unknown")
        source_id = f"{patent_number}:claim-{claim_number}"

        # Each claim is its own chunk (most are <500 tokens)
        chunks.append({
            "source_table": "patent_claims",
            "source_id": source_id,
            "chunk_index": 0,
            "title": f"{patent_number} — Claim {claim_number} ({claim_type})",
            "chunk_text": claim_text,
            "content_hash": content_hash(claim_text),
            "metadata": json.dumps({
                "date": None,
                "url": None,
                "source_label": "PATENT CLAIM",
                "claim_type": claim_type,
                "family_id": family_map.get(patent_number),
            }),
        })

    log(f"  {len(chunks)} claim chunks")
    return chunks


# SEC 10-K / 10-Q section patterns — order matters (match most specific first)
_SEC_SECTION_PATTERNS = [
    # 10-K items
    (r"(?i)\bitem\s+1a[\.\s\-—:]+risk\s+factors", "ITEM 1A - RISK FACTORS"),
    (r"(?i)\bitem\s+1b[\.\s\-—:]", "ITEM 1B - UNRESOLVED STAFF COMMENTS"),
    (r"(?i)\bitem\s+1c[\.\s\-—:]", "ITEM 1C - CYBERSECURITY"),
    (r"(?i)\bitem\s+1[\.\s\-—:]+business", "ITEM 1 - BUSINESS"),
    (r"(?i)\bitem\s+2[\.\s\-—:]+propert", "ITEM 2 - PROPERTIES"),
    (r"(?i)\bitem\s+3[\.\s\-—:]+legal", "ITEM 3 - LEGAL PROCEEDINGS"),
    (r"(?i)\bitem\s+5[\.\s\-—:]+market", "ITEM 5 - MARKET FOR REGISTRANT'S COMMON EQUITY"),
    (r"(?i)\bitem\s+6[\.\s\-—:]", "ITEM 6 - RESERVED"),
    (r"(?i)\bitem\s+7a[\.\s\-—:]+quant", "ITEM 7A - QUANTITATIVE AND QUALITATIVE DISCLOSURES"),
    (r"(?i)\bitem\s+7[\.\s\-—:]+management", "ITEM 7 - MANAGEMENT'S DISCUSSION AND ANALYSIS"),
    (r"(?i)\bitem\s+8[\.\s\-—:]+financial\s+statements", "ITEM 8 - FINANCIAL STATEMENTS"),
    (r"(?i)\bitem\s+9a[\.\s\-—:]+controls", "ITEM 9A - CONTROLS AND PROCEDURES"),
    (r"(?i)\bitem\s+9b[\.\s\-—:]", "ITEM 9B - OTHER INFORMATION"),
    (r"(?i)\bitem\s+9c[\.\s\-—:]", "ITEM 9C - DISCLOSURE REGARDING FOREIGN JURISDICTIONS"),
    (r"(?i)\bitem\s+9[\.\s\-—:]", "ITEM 9 - CHANGES IN AND DISAGREEMENTS"),
    (r"(?i)\bitem\s+10[\.\s\-—:]+director", "ITEM 10 - DIRECTORS AND CORPORATE GOVERNANCE"),
    (r"(?i)\bitem\s+11[\.\s\-—:]+exec", "ITEM 11 - EXECUTIVE COMPENSATION"),
    (r"(?i)\bitem\s+12[\.\s\-—:]", "ITEM 12 - SECURITY OWNERSHIP"),
    (r"(?i)\bitem\s+13[\.\s\-—:]", "ITEM 13 - CERTAIN RELATIONSHIPS"),
    (r"(?i)\bitem\s+14[\.\s\-—:]", "ITEM 14 - PRINCIPAL ACCOUNTANT FEES"),
    (r"(?i)\bitem\s+15[\.\s\-—:]", "ITEM 15 - EXHIBITS AND FINANCIAL STATEMENT SCHEDULES"),
    # 10-Q items
    (r"(?i)\bpart\s+i[\.\s\-—:]+financial\s+information", "PART I - FINANCIAL INFORMATION"),
    (r"(?i)\bpart\s+ii[\.\s\-—:]+other\s+information", "PART II - OTHER INFORMATION"),
    # Subsection headers found inside financial sections
    (r"(?i)\bliquidity\s+and\s+capital\s+resources", "LIQUIDITY AND CAPITAL RESOURCES"),
    (r"(?i)\bcash\s+flows?\b", "CASH FLOWS"),
    (r"(?i)\bresults\s+of\s+operations", "RESULTS OF OPERATIONS"),
    (r"(?i)\bbalance\s+sheets?", "BALANCE SHEETS"),
    (r"(?i)\bstatements?\s+of\s+operations", "STATEMENTS OF OPERATIONS"),
    (r"(?i)\bstatements?\s+of\s+comprehensive", "STATEMENTS OF COMPREHENSIVE INCOME/LOSS"),
    (r"(?i)\bstockholders.?\s+equity", "STOCKHOLDERS' EQUITY"),
    (r"(?i)\brevenue\s+recognition", "REVENUE RECOGNITION"),
]

# Financial sections where chunks get boosted with repeated prefix
_FINANCIAL_SECTIONS = {
    "ITEM 7 - MANAGEMENT'S DISCUSSION AND ANALYSIS",
    "ITEM 7A - QUANTITATIVE AND QUALITATIVE DISCLOSURES",
    "ITEM 8 - FINANCIAL STATEMENTS",
    "PART I - FINANCIAL INFORMATION",
    "LIQUIDITY AND CAPITAL RESOURCES",
    "CASH FLOWS",
    "RESULTS OF OPERATIONS",
    "BALANCE SHEETS",
    "STATEMENTS OF OPERATIONS",
    "STATEMENTS OF COMPREHENSIVE INCOME/LOSS",
    "STOCKHOLDERS' EQUITY",
    "REVENUE RECOGNITION",
}


def _detect_sections(text: str) -> List[tuple]:
    """
    Split filing text into (section_name, section_text) pairs.
    Walks through the text finding section headers. Text before the first
    header gets section_name=None. Returns list of (section_name, text).
    """
    # Build a list of (position, section_name) for all detected headers
    markers = []
    for pattern, section_name in _SEC_SECTION_PATTERNS:
        for m in re.finditer(pattern, text):
            markers.append((m.start(), section_name))

    if not markers:
        return [(None, text)]

    # Sort by position, deduplicate overlapping matches (keep first)
    markers.sort(key=lambda x: x[0])
    deduped = [markers[0]]
    for pos, name in markers[1:]:
        # Skip if too close to previous marker (likely overlapping match)
        if pos - deduped[-1][0] < 50:
            continue
        deduped.append((pos, name))
    markers = deduped

    sections = []
    # Text before first section header
    if markers[0][0] > 0:
        preamble = text[:markers[0][0]].strip()
        if preamble:
            sections.append((None, preamble))

    # Each section runs from its marker to the next
    for idx, (pos, name) in enumerate(markers):
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(text)
        section_text = text[pos:end].strip()
        if section_text:
            sections.append((name, section_text))

    return sections


def extract_filings(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from SEC filings table.

    For 10-K and 10-Q filings, uses section-aware chunking:
    - Detects SEC section headers (Item 7, Item 8, etc.)
    - Prepends section name to each chunk for embedding context
    - Boosts financial sections (MD&A, cash flows, liquidity) by
      repeating the section prefix so the embedding captures it
    - Stores section name in chunk metadata
    """
    log("Fetching SEC filings...")
    rows = supabase_paginate(
        "filings?select=accession_number,form,filing_date,summary,url,content_text"
        "&status=eq.completed"
    )
    log(f"  Found {len(rows)} filings")

    chunks = []
    section_aware_count = 0

    for row in rows:
        accession = row.get("accession_number", "")
        form = row.get("form", "")
        filing_date = row.get("filing_date", "")
        title = f"{form} — {filing_date}"

        # Use summary + content_text
        parts = []
        if row.get("summary"):
            parts.append(f"SUMMARY: {row['summary']}")
        if row.get("content_text"):
            parts.append(row["content_text"])

        full_text = "\n\n".join(parts)
        if not full_text.strip():
            continue

        # Section-aware chunking for 10-K and 10-Q filings
        is_section_aware = form.upper() in ("10-K", "10-Q", "10-K/A", "10-Q/A")
        chunk_index = 0

        if is_section_aware:
            sections = _detect_sections(full_text)
            section_aware_count += 1

            for section_name, section_text in sections:
                section_chunks = chunk_text(section_text)

                for raw_chunk in section_chunks:
                    # Prefix chunk with section context for better embeddings
                    if section_name:
                        is_financial = section_name in _FINANCIAL_SECTIONS
                        # Financial sections get boosted: repeat prefix for
                        # stronger embedding signal on financial queries
                        if is_financial:
                            prefixed = (
                                f"[{section_name}] [FINANCIAL DATA] "
                                f"{section_name}: {raw_chunk}"
                            )
                        else:
                            prefixed = f"[{section_name}]: {raw_chunk}"
                    else:
                        prefixed = raw_chunk
                        is_financial = False

                    chunks.append({
                        "source_table": "filings",
                        "source_id": accession,
                        "chunk_index": chunk_index,
                        "title": title,
                        "chunk_text": prefixed,
                        "content_hash": content_hash(prefixed),
                        "metadata": json.dumps({
                            "date": filing_date,
                            "url": row.get("url"),
                            "source_label": "SEC FILING",
                            "form": form,
                            "section": section_name,
                            "is_financial": is_financial,
                        }),
                    })
                    chunk_index += 1
        else:
            # Non-10-K/10-Q: generic chunking (8-K, S-1, etc.)
            text_chunks = chunk_text(full_text)
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    "source_table": "filings",
                    "source_id": accession,
                    "chunk_index": i,
                    "title": title,
                    "chunk_text": chunk,
                    "content_hash": content_hash(chunk),
                    "metadata": json.dumps({
                        "date": filing_date,
                        "url": row.get("url"),
                        "source_label": "SEC FILING",
                        "form": form,
                    }),
                })

    log(f"  Chunked into {len(chunks)} segments ({section_aware_count} section-aware filings)")
    return chunks


def extract_fcc_filings(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from FCC filings table."""
    log("Fetching FCC filings...")
    rows = supabase_paginate(
        "fcc_filings?select=id,file_number,title,filed_date,ai_summary,source_url,content_text"
    )
    log(f"  Found {len(rows)} FCC filings")

    chunks = []
    for row in rows:
        file_number = row.get("file_number") or row.get("id", "")
        title = row.get("title", "")

        parts = []
        if row.get("ai_summary"):
            parts.append(f"SUMMARY: {row['ai_summary']}")
        if row.get("content_text"):
            parts.append(row["content_text"])

        full_text = "\n\n".join(parts)
        if not full_text.strip():
            continue

        text_chunks = chunk_text(full_text)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "fcc_filings",
                "source_id": file_number,
                "chunk_index": i,
                "title": title,
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "date": row.get("filed_date"),
                    "url": row.get("source_url"),
                    "source_label": "FCC FILING",
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


def extract_press_releases(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from press_releases table."""
    log("Fetching press releases...")
    rows = supabase_paginate(
        "press_releases?select=source_id,title,published_at,url,summary,content_text"
        "&status=eq.completed"
    )
    log(f"  Found {len(rows)} press releases")

    chunks = []
    for row in rows:
        source_id = row.get("source_id", "")
        title = row.get("title", "")
        published_at = row.get("published_at", "")
        date_str = published_at.split("T")[0] if published_at else None

        parts = []
        if title:
            parts.append(title)
        if row.get("summary"):
            parts.append(f"SUMMARY: {row['summary']}")
        if row.get("content_text"):
            parts.append(row["content_text"])

        full_text = "\n\n".join(parts)
        if not full_text.strip():
            continue

        text_chunks = chunk_text(full_text)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "press_releases",
                "source_id": source_id,
                "chunk_index": i,
                "title": title,
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "date": date_str,
                    "url": row.get("url"),
                    "source_label": "PRESS RELEASE",
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


def extract_earnings_transcripts(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from earnings call transcripts (inbox table, source=earnings_call)."""
    log("Fetching earnings call transcripts...")
    rows = supabase_paginate(
        "inbox?select=id,source_id,title,published_at,url,summary,content_text"
        "&source=eq.earnings_call"
        "&status=eq.completed"
    )
    log(f"  Found {len(rows)} transcripts")

    chunks = []
    for row in rows:
        source_id = row.get("source_id") or str(row.get("id", ""))
        title = row.get("title", "")
        published_at = row.get("published_at", "")
        date_str = published_at.split("T")[0] if published_at else None

        parts = []
        if title:
            parts.append(title)
        if row.get("summary"):
            parts.append(f"SUMMARY: {row['summary']}")
        if row.get("content_text"):
            parts.append(row["content_text"])

        full_text = "\n\n".join(parts)
        if not full_text.strip():
            continue

        text_chunks = chunk_text(full_text)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "earnings_transcripts",
                "source_id": source_id,
                "chunk_index": i,
                "title": title,
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "date": date_str,
                    "url": row.get("url"),
                    "source_label": "EARNINGS CALL",
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def extract_spacemob_reports(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from SpaceMob community reports (local .txt files)."""
    import glob as globmod

    report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "research", "spacemob")
    report_dir = os.path.normpath(report_dir)
    log(f"Scanning SpaceMob reports in {report_dir}...")

    txt_files = sorted(globmod.glob(os.path.join(report_dir, "*.txt")))
    if not txt_files:
        log("  No .txt files found")
        return []

    log(f"  Found {len(txt_files)} report(s)")
    chunks = []

    for filepath in txt_files:
        filename = os.path.basename(filepath)
        source_id = filename.replace(".txt", "")
        title = source_id.replace("-", " ").title()

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            continue

        log(f"  {filename}: {len(text)} chars")

        # Use slightly larger chunks for report context (more coherent sections)
        text_chunks = chunk_text(text, chunk_size=3000, overlap=300)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "spacemob_reports",
                "source_id": source_id,
                "chunk_index": i,
                "title": title,
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "date": None,
                    "url": None,
                    "source_label": "SPACEMOB REPORT",
                    "filename": filename,
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


def extract_constellation_knowledge(dry_run: bool = False) -> List[Dict]:
    """Extract constellation architecture from static FCC filings JSON.

    Stored as source_table='fcc_filings' so existing search picks them up.
    """
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "research", "asts", "filings", "fcc-filings.json")
    if not os.path.exists(json_path):
        log(f"  Constellation JSON not found: {json_path}")
        return []

    with open(json_path, "r") as f:
        data = json.load(f)

    chunks = []
    fetched = data.get("fetchedAt", "2026-01-25")[:10]
    fcc_url = data.get("resources", {}).get("fccReportCompany", "")

    # Chunk 1: Constellation overview + shells
    constellation = data.get("constellation", {})
    shells = constellation.get("shells", [])
    shell_lines = []
    for i, s in enumerate(shells, 1):
        shell_lines.append(
            f"Shell {i}: {s['count']} satellites at {s['altitude_km']} km altitude, "
            f"{s['inclination']}° inclination — {s['description']}"
        )
    overview = (
        f"AST SpaceMobile FCC Constellation Architecture\n\n"
        f"Total authorized satellites: {constellation.get('totalSatellites', 248)}\n"
        f"Number of orbital shells: {len(shells)}\n\n"
        f"Orbital Shell Breakdown:\n" + "\n".join(shell_lines) + "\n\n"
        f"The constellation uses {len(shells)} orbital shells at different altitudes and inclinations. "
        f"The main constellation of {shells[1]['count'] if len(shells) > 1 else 'N/A'} satellites at "
        f"{shells[1]['altitude_km'] if len(shells) > 1 else 'N/A'} km provides primary coverage. "
        f"A polar shell at {shells[2]['inclination'] if len(shells) > 2 else 'N/A'}° inclination "
        f"extends coverage to high latitudes. "
        f"The filing reference is SAT-AMD-20240311-00053 (248-satellite constellation amendment)."
    )
    chunks.append({
        "source_table": "fcc_filings",
        "source_id": "constellation-shells",
        "chunk_index": 0,
        "title": "AST SpaceMobile Constellation Architecture — Orbital Shells",
        "chunk_text": overview,
        "content_hash": content_hash(overview),
        "metadata": json.dumps({
            "date": fetched,
            "url": fcc_url,
            "source_label": "FCC FILING",
        }),
    })

    # Chunk 2: Satellite launches
    launched = constellation.get("blueBirdsLaunched", [])
    planned = constellation.get("plannedLaunches", [])
    launch_text = "AST SpaceMobile Satellite Launch History\n\n"
    for sat in launched:
        launch_text += f"- {sat['name']}: Launched {sat['launchDate']}, Status: {sat['status']}\n"
    if planned:
        launch_text += "\nPlanned launches:\n"
        for sat in planned:
            launch_text += f"- {sat['name']}: Target {sat['targetDate']}, Vehicle: {sat.get('vehicle', 'TBD')}\n"
    chunks.append({
        "source_table": "fcc_filings",
        "source_id": "constellation-launches",
        "chunk_index": 0,
        "title": "AST SpaceMobile Satellite Launch History",
        "chunk_text": launch_text,
        "content_hash": content_hash(launch_text),
        "metadata": json.dumps({
            "date": fetched,
            "url": fcc_url,
            "source_label": "FCC FILING",
        }),
    })

    # Chunk 3: Spectrum bands
    bands = data.get("spectrumBands", [])
    spectrum_text = "AST SpaceMobile FCC Spectrum Allocations\n\n"
    for b in bands:
        partner = f" (Partner: {b['partner']})" if b.get("partner") else ""
        status = f" [{b['status']}]" if b.get("status") else ""
        spectrum_text += f"- {b['band']}: {b['direction']} — {b['use']}{partner}{status}\n"
    chunks.append({
        "source_table": "fcc_filings",
        "source_id": "constellation-spectrum",
        "chunk_index": 0,
        "title": "AST SpaceMobile FCC Spectrum Allocations",
        "chunk_text": spectrum_text,
        "content_hash": content_hash(spectrum_text),
        "metadata": json.dumps({
            "date": fetched,
            "url": fcc_url,
            "source_label": "FCC FILING",
        }),
    })

    # Chunk 4: Key filings + dockets
    filings = data.get("keyFilings", [])
    dockets = data.get("keyDockets", [])
    filings_text = "AST SpaceMobile Key FCC Filings and Dockets\n\n"
    for f_item in filings:
        filings_text += (
            f"- {f_item['type']}: {f_item.get('fileNumber', 'N/A')} — "
            f"{f_item['description']} (Status: {f_item['status']})\n"
        )
    filings_text += "\nKey regulatory dockets:\n"
    for d in dockets:
        filings_text += f"- {d['docket']}: {d['title']} — {d['description']}\n"
    chunks.append({
        "source_table": "fcc_filings",
        "source_id": "constellation-filings",
        "chunk_index": 0,
        "title": "AST SpaceMobile Key FCC Filings and Dockets",
        "chunk_text": filings_text,
        "content_hash": content_hash(filings_text),
        "metadata": json.dumps({
            "date": fetched,
            "url": fcc_url,
            "source_label": "FCC FILING",
        }),
    })

    log(f"  Created {len(chunks)} constellation knowledge chunks")
    return chunks


def extract_x_posts(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from x_posts table. Each tweet = 1 chunk (already short)."""
    log("Fetching X posts (classified only)...")
    rows = supabase_paginate(
        "x_posts?select=source_id,tweet_id,author_username,content_text,published_at,summary,sentiment,signal_type,url&sentiment=not.is.null"
    )
    log(f"  Found {len(rows)} X posts")

    chunks = []
    for row in rows:
        source_id = row.get("source_id", "")
        username = row.get("author_username", "")
        text = row.get("content_text", "").strip()
        summary = row.get("summary", "")

        if not text:
            continue

        # Format: @username: tweet text\nSummary: ...
        full_text = f"@{username}: {text}"
        if summary:
            full_text += f"\nSummary: {summary}"

        published_at = row.get("published_at", "")
        date_str = published_at.split("T")[0] if published_at else None

        # Each tweet is one chunk (already short enough)
        chunks.append({
            "source_table": "x_posts",
            "source_id": source_id,
            "chunk_index": 0,
            "title": f"@{username}: {text[:80]}",
            "chunk_text": full_text,
            "content_hash": content_hash(full_text),
            "metadata": json.dumps({
                "date": date_str,
                "url": row.get("url"),
                "source_label": "X POST",
                "sentiment": row.get("sentiment"),
                "signal_type": row.get("signal_type"),
            }),
        })

    log(f"  {len(chunks)} tweet chunks")
    return chunks


def extract_fcc_attachments(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from fcc_filing_attachments table (technical docs, PDFs)."""
    log("Fetching FCC filing attachments...")
    rows = supabase_paginate(
        "fcc_filing_attachments?select=id,file_number,filename,description,content_text,fetched_at"
        "&content_text=not.is.null"
        "&order=file_number.asc"
    )
    log(f"  Found {len(rows)} attachments with content")

    chunks = []
    for row in rows:
        source_id = f"{row.get('file_number', '')}:{row.get('id', '')}"
        filename = row.get("filename", "")
        file_number = row.get("file_number", "")
        description = row.get("description", "")
        content = row.get("content_text", "")

        if not content or not content.strip():
            continue

        # Skip very short content (likely extraction artifacts)
        if len(content.strip()) < 100:
            continue

        # Prepend context
        header = f"FCC Filing {file_number}"
        if filename:
            header += f" — {filename}"
        full_text = f"{header}\n\n{content}"

        text_chunks = chunk_text(full_text)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "fcc_filing_attachments",
                "source_id": source_id,
                "chunk_index": i,
                "title": filename or f"FCC Attachment {file_number}",
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "file_number": file_number,
                    "filename": filename,
                    "description": description,
                    "source_label": "FCC ATTACHMENT",
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


def extract_sec_exhibits(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from sec_filing_exhibits table."""
    log("Fetching SEC filing exhibits...")
    rows = supabase_paginate(
        "sec_filing_exhibits?select=id,accession_number,exhibit_number,exhibit_type,description,filename,content_text,fetched_at"
        "&content_text=not.is.null"
        "&order=accession_number.asc"
    )
    log(f"  Found {len(rows)} exhibits with content")

    chunks = []
    for row in rows:
        accession = row.get("accession_number", "")
        exhibit_num = row.get("exhibit_number", "")
        source_id = f"{accession}:ex-{exhibit_num}"
        exhibit_type = row.get("exhibit_type", "") or row.get("description", "")
        filename = row.get("filename", "")
        fetched_at = row.get("fetched_at", "")
        content = row.get("content_text", "")

        if not content or not content.strip():
            continue

        if len(content.strip()) < 100:
            continue

        header = f"SEC Exhibit {exhibit_num}"
        if exhibit_type:
            header += f" — {exhibit_type}"
        full_text = f"{header}\n\n{content}"

        text_chunks = chunk_text(full_text)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "sec_filing_exhibits",
                "source_id": source_id,
                "chunk_index": i,
                "title": exhibit_type or f"Exhibit {exhibit_num}",
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "accession_number": accession,
                    "exhibit_number": exhibit_num,
                    "filename": filename,
                    "source_label": "SEC EXHIBIT",
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


def extract_inbox(dry_run: bool = False) -> List[Dict]:
    """Extract chunks from inbox table (news, press_release sources)."""
    log("Fetching inbox items...")
    rows = supabase_paginate(
        "inbox?select=id,source_id,source,title,published_at,url,summary,content_text"
        "&status=eq.completed"
        "&source=neq.earnings_call"
    )
    log(f"  Found {len(rows)} inbox items")

    chunks = []
    for row in rows:
        source_id = row.get("source_id") or str(row.get("id", ""))
        title = row.get("title", "")
        published_at = row.get("published_at", "")
        date_str = published_at.split("T")[0] if published_at else None

        parts = []
        if title:
            parts.append(title)
        if row.get("summary"):
            parts.append(f"SUMMARY: {row['summary']}")
        if row.get("content_text"):
            parts.append(row["content_text"])

        full_text = "\n\n".join(parts)
        if not full_text.strip():
            continue

        text_chunks = chunk_text(full_text)
        for i, chunk in enumerate(text_chunks):
            chunks.append({
                "source_table": "inbox",
                "source_id": source_id,
                "chunk_index": i,
                "title": title,
                "chunk_text": chunk,
                "content_hash": content_hash(chunk),
                "metadata": json.dumps({
                    "date": date_str,
                    "url": row.get("url"),
                    "inbox_source": row.get("source"),
                    "source_label": "NEWS",
                }),
            })

    log(f"  Chunked into {len(chunks)} segments")
    return chunks


TABLE_EXTRACTORS = {
    "patents": extract_patents,
    "patent_claims": extract_patent_claims,
    "filings": extract_filings,
    "fcc_filings": extract_fcc_filings,
    "fcc_filing_attachments": extract_fcc_attachments,
    "sec_filing_exhibits": extract_sec_exhibits,
    "inbox": extract_inbox,
    "press_releases": extract_press_releases,
    "earnings_transcripts": extract_earnings_transcripts,
    "spacemob_reports": extract_spacemob_reports,
    "constellation": extract_constellation_knowledge,
    "x_posts": extract_x_posts,
}


def get_existing_hashes(source_table: str) -> set:
    """Get existing content hashes to skip unchanged chunks."""
    rows = supabase_paginate(
        f"brain_chunks?select=source_id,chunk_index,content_hash"
        f"&source_table=eq.{source_table}"
    )
    return {
        (r["source_id"], r["chunk_index"], r.get("content_hash", ""))
        for r in rows
    }


def embed_and_upsert(chunks: List[Dict], dry_run: bool = False) -> int:
    """Embed chunks in batches and upsert to brain_chunks."""
    if not chunks:
        return 0

    log(f"  Embedding {len(chunks)} chunks...")
    total_embedded = 0
    total_tokens = 0

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        texts = [c["chunk_text"] for c in batch]

        if dry_run:
            total_embedded += len(batch)
            continue

        try:
            embeddings = get_embeddings(texts)
        except Exception as e:
            log(f"  Embedding error at batch {i}: {e}")
            continue

        # Attach embeddings to chunks
        rows_to_upsert = []
        for chunk, embedding in zip(batch, embeddings):
            row = dict(chunk)
            # Convert embedding list to pgvector format string
            row["embedding"] = f"[{','.join(str(x) for x in embedding)}]"
            rows_to_upsert.append(row)

        upserted = supabase_upsert(
            "brain_chunks", rows_to_upsert,
            on_conflict="source_table,source_id,chunk_index"
        )
        total_embedded += upserted

        # Estimate tokens (~4 chars per token)
        total_tokens += sum(len(t) for t in texts) // 4

        if i + EMBED_BATCH_SIZE < len(chunks):
            time.sleep(EMBED_DELAY)

        # Progress
        pct = min(100, int((i + len(batch)) / len(chunks) * 100))
        log(f"  [{pct}%] Embedded {total_embedded}/{len(chunks)} chunks")

    cost_estimate = total_tokens / 1_000_000 * 0.02
    log(f"  Done. ~{total_tokens:,} tokens, ~${cost_estimate:.4f} estimated cost")
    return total_embedded


def run(tables: Optional[List[str]] = None, force: bool = False,
        dry_run: bool = False):
    """Main pipeline."""
    log("=" * 60)
    log("BRAIN EMBEDDING WORKER")
    log(f"  Mode: {'DRY RUN' if dry_run else 'FORCE' if force else 'INCREMENTAL'}")
    log(f"  Tables: {', '.join(tables) if tables else 'ALL'}")
    log("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    if not OPENAI_API_KEY and not dry_run:
        log("ERROR: OPENAI_API_KEY required for embedding")
        sys.exit(1)

    active_tables = tables or list(TABLE_EXTRACTORS.keys())
    grand_total = 0

    for table in active_tables:
        if table not in TABLE_EXTRACTORS:
            log(f"Unknown table: {table}, skipping")
            continue

        log(f"\n--- {table.upper()} ---")

        # Extract chunks
        all_chunks = TABLE_EXTRACTORS[table](dry_run)
        if not all_chunks:
            log(f"  No content to embed")
            continue

        # Filter unchanged chunks (incremental mode)
        if not force:
            existing = get_existing_hashes(table)
            new_chunks = [
                c for c in all_chunks
                if (c["source_id"], c["chunk_index"], c.get("content_hash", ""))
                not in existing
            ]
            skipped = len(all_chunks) - len(new_chunks)
            if skipped:
                log(f"  Skipping {skipped} unchanged chunks")
            all_chunks = new_chunks

        if not all_chunks:
            log(f"  Everything up to date")
            continue

        # Embed and upsert
        count = embed_and_upsert(all_chunks, dry_run)
        grand_total += count

    log(f"\n{'=' * 60}")
    log(f"TOTAL: {grand_total} chunks {'would be' if dry_run else ''} embedded")
    log("=" * 60)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed documents for Brain search")
    parser.add_argument("--force", action="store_true", help="Re-embed all chunks")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--table", type=str, help="Single table to process",
                        choices=list(TABLE_EXTRACTORS.keys()))
    args = parser.parse_args()

    tables = [args.table] if args.table else None
    run(tables=tables, force=args.force, dry_run=args.dry_run)
