"""
Document Gap Analyzer
Semantically analyzes FCC filing attachments and SEC exhibits using Claude
to identify referenced documents we don't have in our database.
"""

import json
import os
import time
import urllib.request
import urllib.parse
import ssl
import sys
from collections import defaultdict

# Config
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = "claude-haiku-4-5-20251001"

# SSL context
ctx = ssl.create_default_context()


def supabase_get(table, params):
    """Fetch from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode())


def call_claude(prompt, text, max_retries=3):
    """Call Anthropic API with retry."""
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": f"{prompt}\n\n---\nDOCUMENT TEXT:\n{text[:8000]}"}]
    }).encode()

    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload, headers={
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data["content"][0]["text"]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Retry {attempt+1} in {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"  FAILED after {max_retries} attempts: {e}")
                return None


ANALYSIS_PROMPT = """You are analyzing an FCC/SEC filing attachment about AST SpaceMobile (ASTS) satellites.

List ALL external documents, filings, reports, standards, or agreements referenced in this text that are NOT part of this document itself.

For each referenced document, output a JSON object on its own line with these fields:
- "name": exact document name/identifier as written
- "type": one of: "fcc_filing", "itu_document", "technical_standard", "commercial_agreement", "government_doc", "international_regulator", "third_party_report", "academic_paper", "legal_case", "other"
- "identifier": file number, docket number, standard number, date, or other specific identifier (null if none)
- "public": true/false whether it's likely publicly accessible
- "context": one sentence about why it's referenced

Output ONLY the JSON objects, one per line. No markdown, no commentary. If no references found, output: {"none": true}"""


def analyze_batch(docs, source_label):
    """Analyze a batch of documents and return all references found."""
    all_refs = []
    total = len(docs)

    for i, doc in enumerate(docs):
        content = doc.get("content_text") or ""
        if len(content) < 200:
            continue

        label = doc.get("filename") or doc.get("form") or doc.get("id")
        file_num = doc.get("file_number") or doc.get("filing_date") or ""
        print(f"  [{i+1}/{total}] {source_label}: {label} ({file_num}) — {len(content)} chars")

        result = call_claude(ANALYSIS_PROMPT, content)
        if not result:
            continue

        # Parse JSON lines
        for line in result.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "none" in obj:
                    continue
                obj["source_doc"] = f"{source_label}: {label}"
                obj["source_file_number"] = file_num
                all_refs.append(obj)
            except json.JSONDecodeError:
                # Try to extract JSON from the line
                if "{" in line and "}" in line:
                    try:
                        start = line.index("{")
                        end = line.rindex("}") + 1
                        obj = json.loads(line[start:end])
                        if "none" not in obj:
                            obj["source_doc"] = f"{source_label}: {label}"
                            obj["source_file_number"] = file_num
                            all_refs.append(obj)
                    except:
                        pass

        # Rate limiting — 1s between calls
        time.sleep(1)

    return all_refs


def deduplicate_refs(refs):
    """Deduplicate references by identifier or name."""
    seen = {}
    for ref in refs:
        key = (ref.get("identifier") or ref.get("name", "")).strip().lower()
        if not key:
            continue
        if key in seen:
            # Merge source docs
            existing = seen[key]
            if ref.get("source_doc") not in existing.get("found_in", []):
                existing.setdefault("found_in", [existing.get("source_doc", "")]).append(ref.get("source_doc", ""))
            existing["mention_count"] = existing.get("mention_count", 1) + 1
        else:
            ref["mention_count"] = 1
            ref["found_in"] = [ref.get("source_doc", "")]
            seen[key] = ref
    return sorted(seen.values(), key=lambda x: -x.get("mention_count", 0))


def categorize(refs):
    """Categorize deduplicated refs."""
    categories = {
        "fcc_filing": [],
        "itu_document": [],
        "technical_standard": [],
        "commercial_agreement": [],
        "government_doc": [],
        "international_regulator": [],
        "third_party_report": [],
        "academic_paper": [],
        "legal_case": [],
        "other": [],
    }
    for ref in refs:
        cat = ref.get("type", "other")
        if cat not in categories:
            cat = "other"
        categories[cat].append(ref)
    return categories


def print_report(categories):
    """Print the final gap analysis report."""
    print("\n" + "=" * 80)
    print("DOCUMENT GAP ANALYSIS — AST SpaceMobile Filing References")
    print("=" * 80)

    labels = {
        "fcc_filing": "FCC FILINGS WE DON'T HAVE",
        "itu_document": "ITU DOCUMENTS",
        "technical_standard": "TECHNICAL STANDARDS (ITU-R, 3GPP, etc.)",
        "commercial_agreement": "COMMERCIAL AGREEMENTS",
        "government_doc": "GOVERNMENT AGENCY DOCS (NASA, NTIA, DoD, FAA)",
        "international_regulator": "INTERNATIONAL REGULATOR FILINGS",
        "third_party_report": "THIRD-PARTY REPORTS / STUDIES",
        "academic_paper": "ACADEMIC PAPERS",
        "legal_case": "LEGAL CASES",
        "other": "OTHER REFERENCES",
    }

    total = 0
    for cat, label in labels.items():
        items = categories.get(cat, [])
        if not items:
            continue
        total += len(items)
        print(f"\n{'─' * 80}")
        print(f"  {label} ({len(items)} documents)")
        print(f"{'─' * 80}")
        for item in items:
            name = item.get("name", "Unknown")
            ident = item.get("identifier") or "—"
            public = "PUBLIC" if item.get("public") else "RESTRICTED"
            mentions = item.get("mention_count", 1)
            context = item.get("context", "")
            found_in = item.get("found_in", [])

            print(f"\n  [{public}] {name}")
            print(f"    ID: {ident}")
            print(f"    Context: {context}")
            print(f"    Mentions: {mentions}x across {len(found_in)} doc(s)")
            if len(found_in) <= 3:
                for src in found_in:
                    print(f"      ← {src}")

    print(f"\n{'=' * 80}")
    print(f"TOTAL UNIQUE REFERENCED DOCUMENTS: {total}")
    print(f"{'=' * 80}")


def main():
    print("=" * 80)
    print("Document Gap Analyzer — Semantic Analysis")
    print("=" * 80)

    # Phase 1: Fetch FCC filing attachments
    print("\n[PHASE 1] Fetching FCC filing attachments...")
    try:
        fcc_docs = supabase_get("fcc_filing_attachments", {
            "select": "id,file_number,filename,content_text,file_size_bytes",
            "content_text": "not.is.null",
            "order": "file_size_bytes.desc",
            "limit": "50",
        })
        print(f"  Found {len(fcc_docs)} FCC attachments with content")
    except Exception as e:
        print(f"  FCC attachments table error: {e}")
        # Try fcc_filings instead
        print("  Falling back to fcc_filings table...")
        try:
            fcc_docs = supabase_get("fcc_filings", {
                "select": "id,file_number,title,content_text",
                "content_text": "not.is.null",
                "order": "filed_date.desc",
                "limit": "50",
            })
            # Normalize field names
            for d in fcc_docs:
                d["filename"] = d.get("title", "")
            print(f"  Found {len(fcc_docs)} FCC filings with content")
        except Exception as e2:
            print(f"  FCC filings also failed: {e2}")
            fcc_docs = []

    # Phase 2: Fetch SEC filings (largest exhibits)
    print("\n[PHASE 2] Fetching SEC filings...")
    try:
        sec_docs = supabase_get("filings", {
            "select": "id,form,filing_date,content_text",
            "content_text": "not.is.null",
            "order": "filing_date.desc",
            "limit": "20",
        })
        # Normalize
        for d in sec_docs:
            d["filename"] = f"{d.get('form', '')} ({d.get('filing_date', '')})"
            d["file_number"] = d.get("filing_date", "")
        print(f"  Found {len(sec_docs)} SEC filings with content")
    except Exception as e:
        print(f"  SEC filings error: {e}")
        sec_docs = []

    if not fcc_docs and not sec_docs:
        print("\nNo documents to analyze. Exiting.")
        return

    # Phase 3: Analyze with Claude
    print(f"\n[PHASE 3] Analyzing {len(fcc_docs)} FCC + {len(sec_docs)} SEC docs with Claude ({MODEL})...")
    all_refs = []

    if fcc_docs:
        print("\n--- FCC Attachments ---")
        fcc_refs = analyze_batch(fcc_docs, "FCC")
        all_refs.extend(fcc_refs)
        print(f"  → Found {len(fcc_refs)} references in FCC docs")

    if sec_docs:
        print("\n--- SEC Filings ---")
        sec_refs = analyze_batch(sec_docs, "SEC")
        all_refs.extend(sec_refs)
        print(f"  → Found {len(sec_refs)} references in SEC docs")

    print(f"\n[PHASE 4] Deduplicating {len(all_refs)} total references...")
    deduped = deduplicate_refs(all_refs)
    print(f"  → {len(deduped)} unique documents")

    # Phase 5: Categorize and report
    categories = categorize(deduped)
    print_report(categories)

    # Save raw data
    output_path = "/Users/gabriel/Desktop/short_gravity/scripts/data-fetchers/document_gap_analysis.json"
    with open(output_path, "w") as f:
        json.dump({
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_analyzed": len(fcc_docs) + len(sec_docs),
            "total_references": len(all_refs),
            "unique_references": len(deduped),
            "categories": {k: v for k, v in categories.items() if v},
        }, f, indent=2, default=str)
    print(f"\nRaw data saved to: {output_path}")


if __name__ == "__main__":
    main()
