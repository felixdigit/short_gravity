#!/usr/bin/env python3
"""
Query Signal Analyzer — Compound Opportunity #3

Analyzes brain_query_log to identify:
- Trending topics (what users ask about most)
- Coverage gaps (queries with low result counts)
- Source utilization (which data sources get used vs ignored)
- Related document clusters (from source_cooccurrence)

Run:
  cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 query_signal_analyzer.py
  python3 query_signal_analyzer.py --days 7       # Last 7 days
  python3 query_signal_analyzer.py --days 30      # Last 30 days
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def supabase_get(endpoint: str) -> List[Dict]:
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.read().decode()}")
        return []


def analyze_queries(days: int = 7):
    """Analyze recent brain queries for signals."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    print(f"\n{'='*60}")
    print(f"  QUERY SIGNAL REPORT — Last {days} days")
    print(f"{'='*60}\n")

    # Fetch query logs
    logs = supabase_get(
        f"brain_query_log?select=query,search_query,source_counts,result_count,has_url,latency_ms,created_at"
        f"&created_at=gte.{since}&order=created_at.desc&limit=500"
    )

    if not logs:
        print("No query logs found. Has the migration been run?")
        return

    print(f"Total queries: {len(logs)}")

    # ── Trending Topics ──────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  TRENDING TOPICS")
    print(f"{'─'*40}\n")

    # Extract meaningful terms from queries
    word_freq: Counter = Counter()
    stop_words = {
        "what", "how", "does", "is", "the", "a", "an", "of", "in", "for",
        "to", "and", "or", "with", "about", "can", "do", "this", "that",
        "are", "was", "were", "be", "been", "has", "have", "had", "will",
        "would", "could", "should", "may", "might", "their", "they", "them",
        "its", "it", "from", "on", "at", "by", "as", "not", "but", "which",
        "who", "when", "where", "why", "me", "my", "tell", "explain",
        "asts", "ast", "spacemobile", "space", "mobile",
    }

    for log in logs:
        q = log.get("query", "").lower()
        words = [w.strip(".,?!\"'()[]") for w in q.split()]
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        word_freq.update(words)

    # Bigrams for richer topic detection
    bigram_freq: Counter = Counter()
    for log in logs:
        q = log.get("query", "").lower()
        words = [w.strip(".,?!\"'()[]") for w in q.split()]
        words = [w for w in words if len(w) > 2 and w not in stop_words]
        for i in range(len(words) - 1):
            bigram_freq[f"{words[i]} {words[i+1]}"] += 1

    print("Top single terms:")
    for term, count in word_freq.most_common(15):
        bar = "█" * min(count, 30)
        print(f"  {term:<25} {count:>3}  {bar}")

    if bigram_freq:
        print("\nTop phrases:")
        for phrase, count in bigram_freq.most_common(10):
            if count >= 2:
                bar = "█" * min(count, 30)
                print(f"  {phrase:<25} {count:>3}  {bar}")

    # ── Coverage Gaps ────────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  COVERAGE GAPS (low result queries)")
    print(f"{'─'*40}\n")

    low_result_queries = [
        log for log in logs
        if (log.get("result_count") or 0) <= 2
    ]

    if low_result_queries:
        print(f"Queries with ≤2 results: {len(low_result_queries)} / {len(logs)} ({100*len(low_result_queries)//len(logs)}%)\n")
        # Group similar low-result queries
        gap_topics: Counter = Counter()
        for log in low_result_queries:
            q = log.get("query", "").lower()[:80]
            gap_topics[q] += 1
        for query, count in gap_topics.most_common(10):
            print(f"  [{count}x] {query}")
    else:
        print("No low-result queries — archive coverage is strong.")

    # ── Source Utilization ───────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  SOURCE UTILIZATION")
    print(f"{'─'*40}\n")

    source_totals: Counter = Counter()
    source_appearances: Counter = Counter()
    for log in logs:
        counts = log.get("source_counts") or {}
        if isinstance(counts, str):
            try:
                counts = json.loads(counts)
            except Exception:
                continue
        for source, count in counts.items():
            source_totals[source] += count
            source_appearances[source] += 1

    all_sources = [
        "filing", "fcc_filing", "patent", "patent_claim",
        "press_release", "earnings_transcript", "x_post",
        "glossary", "cash_position", "short_interest", "signal",
    ]

    for source in all_sources:
        total = source_totals.get(source, 0)
        appearances = source_appearances.get(source, 0)
        pct = 100 * appearances // len(logs) if logs else 0
        bar = "█" * min(pct, 50)
        status = "" if pct > 10 else " ⚠️ UNDERUSED" if pct > 0 else " ❌ NEVER USED"
        print(f"  {source:<25} {appearances:>4} queries ({pct:>2}%)  {bar}{status}")

    # ── URL Usage ────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  URL ANALYSIS")
    print(f"{'─'*40}\n")

    url_queries = [log for log in logs if log.get("has_url")]
    print(f"Queries with URLs: {len(url_queries)} / {len(logs)} ({100*len(url_queries)//len(logs) if logs else 0}%)")

    # ── Latency ──────────────────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  LATENCY DISTRIBUTION")
    print(f"{'─'*40}\n")

    latencies = [log.get("latency_ms", 0) for log in logs if log.get("latency_ms")]
    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p90 = latencies[int(len(latencies) * 0.9)]
        p99 = latencies[int(len(latencies) * 0.99)]
        print(f"  P50: {p50:>6}ms")
        print(f"  P90: {p90:>6}ms")
        print(f"  P99: {p99:>6}ms")
        print(f"  Max: {max(latencies):>6}ms")

    # ── Source Relationships ─────────────────────────────────────
    print(f"\n{'─'*40}")
    print("  SOURCE RELATIONSHIPS (co-occurrence)")
    print(f"{'─'*40}\n")

    cooc = supabase_get(
        f"source_cooccurrence?select=source_a,source_b&created_at=gte.{since}&limit=1000"
    )

    if cooc:
        pair_freq: Counter = Counter()
        for row in cooc:
            pair = tuple(sorted([row["source_a"], row["source_b"]]))
            pair_freq[pair] += 1

        print(f"Total co-occurrences: {len(cooc)}")
        print(f"Unique pairs: {len(pair_freq)}\n")
        print("Top related document pairs:")
        for (a, b), count in pair_freq.most_common(10):
            a_short = a.split(":")[0] + ":" + a.split(":")[-1][:20]
            b_short = b.split(":")[0] + ":" + b.split(":")[-1][:20]
            print(f"  {count:>3}x  {a_short}  ↔  {b_short}")
    else:
        print("No co-occurrence data yet. Will populate as brain queries run.")

    print(f"\n{'='*60}")
    print(f"  Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze brain query signals")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    args = parser.parse_args()

    if not SUPABASE_SERVICE_KEY:
        print("Error: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    analyze_queries(args.days)


if __name__ == "__main__":
    main()
