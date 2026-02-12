#!/usr/bin/env python3
"""
Signal Scanner — Cross-Source Anomaly Detection for ASTS Intelligence

Scans across all data sources (filings, patents, FCC, X posts, short interest)
to detect cross-source signals and anomalies that no single source reveals.

Detectors:
  1. Sentiment Shift     — Community sentiment diverges from rolling baseline
  2. Filing Cluster      — Multiple SEC/FCC filings in short window (unusual activity)
  3. FCC Status Change   — Grants, new applications, status transitions
  4. Cross-Source        — Filing drops while X sentiment spikes (correlated events)
  5. Short Interest      — Significant changes in short positioning
  6. Patent-Deployment   — Patent technology referenced in recent filings/PRs

Run:
  cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 signal_scanner.py
  cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 signal_scanner.py --dry-run

Schedule: Daily via GitHub Actions
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ── Configuration ────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── Category & Confidence Mapping ────────────────────────────────
# Every signal_type maps to a category and base confidence score.
# These populate the new columns from migration 022.

SIGNAL_CATEGORY_MAP: Dict[str, Dict[str, Any]] = {
    "sentiment_shift":          {"category": "market",     "confidence_score": 0.60},
    "filing_cluster":           {"category": "regulatory", "confidence_score": 0.90},
    "fcc_status_change":        {"category": "regulatory", "confidence_score": 0.95},
    "cross_source":             {"category": "community",  "confidence_score": 0.80},
    "short_interest_spike":     {"category": "market",     "confidence_score": 0.70},
    "new_content":              {"category": "corporate",  "confidence_score": 0.50},
    "patent_regulatory_crossref": {"category": "ip",       "confidence_score": 0.85},
    "earnings_language_shift":  {"category": "corporate",  "confidence_score": 0.75},
}


def utc_iso(dt: datetime) -> str:
    """Format datetime as ISO string safe for Supabase URL params (Z suffix, no +00:00)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── HTTP Utilities ───────────────────────────────────────────────────

def supabase_request(method: str, endpoint: str, data: Optional[Any] = None) -> Any:
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
        log(f"  Supabase error: {e.code} - {error_body}")
        raise


def supabase_paginate(endpoint: str) -> List[Dict]:
    """Paginate past Supabase 1000-row limit."""
    all_rows: List[Dict] = []
    offset = 0
    batch = 1000
    while True:
        sep = "&" if "?" in endpoint else "?"
        result = supabase_request("GET", f"{endpoint}{sep}limit={batch}&offset={offset}")
        if not result:
            break
        all_rows.extend(result)
        if len(result) < batch:
            break
        offset += batch
    return all_rows


def haiku_classify(prompt: str, max_tokens: int = 500) -> str:
    """Call Claude Haiku for fast classification/synthesis."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["content"][0]["text"].strip()


def fingerprint(*parts: str) -> str:
    """Create a deterministic fingerprint for dedup."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def store_signal(signal: Dict, dry_run: bool = False) -> bool:
    """Store a signal, skip if fingerprint already exists.
    Auto-populates category and confidence_score from SIGNAL_CATEGORY_MAP."""
    # Auto-populate category + confidence from mapping
    sig_type = signal.get("signal_type", "")
    mapping = SIGNAL_CATEGORY_MAP.get(sig_type, {})
    if "category" not in signal and "category" in mapping:
        signal["category"] = mapping["category"]
    if "confidence_score" not in signal and "confidence_score" in mapping:
        signal["confidence_score"] = mapping["confidence_score"]

    fp = signal.get("fingerprint", "")
    if dry_run:
        log(f"  [DRY RUN] {signal['severity'].upper()} [{signal.get('category', '?')}] — {signal['title']}")
        return True

    try:
        # Check if fingerprint exists
        existing = supabase_request("GET", f"signals?fingerprint=eq.{fp}&select=id&limit=1")
        if existing:
            return False  # Already detected

        supabase_request("POST", "signals", signal)
        return True
    except Exception as e:
        log(f"  Error storing signal: {e}")
        return False


# ── Detector 1: Sentiment Shift ─────────────────────────────────────

def detect_sentiment_shifts(dry_run: bool = False) -> List[Dict]:
    """Compare 7-day vs 30-day sentiment. Flag significant divergences."""
    log("Scanning: Sentiment shifts...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)
    d7 = utc_iso(now - timedelta(days=7))
    d30 = utc_iso(now - timedelta(days=30))

    # Get 30-day tweets with sentiment
    tweets_30d = supabase_paginate(
        f"x_posts?select=sentiment,published_at,author_username,content_text"
        f"&sentiment=not.is.null&published_at=gte.{d30}&order=published_at.desc"
    )

    if len(tweets_30d) < 20:
        log(f"  Only {len(tweets_30d)} tweets in 30d — skipping")
        return signals

    # Split into 7d and older
    tweets_7d = [t for t in tweets_30d if t.get("published_at", "") >= d7]
    tweets_older = [t for t in tweets_30d if t.get("published_at", "") < d7]

    if len(tweets_7d) < 5:
        log(f"  Only {len(tweets_7d)} tweets in 7d — skipping")
        return signals

    def sentiment_score(tweets: List[Dict]) -> Tuple[float, Dict]:
        counts = {"bullish": 0, "bearish": 0, "neutral": 0, "informational": 0}
        for t in tweets:
            s = t.get("sentiment", "neutral")
            counts[s] = counts.get(s, 0) + 1
        total = sum(counts.values()) or 1
        # Score: -1 (all bearish) to +1 (all bullish)
        score = (counts["bullish"] - counts["bearish"]) / total
        return score, counts

    score_7d, counts_7d = sentiment_score(tweets_7d)
    score_30d, counts_30d = sentiment_score(tweets_30d)
    delta = score_7d - score_30d

    log(f"  7d sentiment: {score_7d:+.2f} ({len(tweets_7d)} tweets, bull={counts_7d['bullish']} bear={counts_7d['bearish']})")
    log(f"  30d sentiment: {score_30d:+.2f} ({len(tweets_30d)} tweets)")
    log(f"  Delta: {delta:+.2f}")

    # Threshold: significant shift
    if abs(delta) >= 0.15:
        direction = "bullish" if delta > 0 else "bearish"
        severity = "high" if abs(delta) >= 0.25 else "medium"

        # Get representative recent tweets
        relevant = [t for t in tweets_7d if t.get("sentiment") == direction][:5]
        source_refs = [
            {
                "table": "x_posts",
                "title": f"@{t.get('author_username', '?')}: {(t.get('content_text', '')[:80])}",
                "date": t.get("published_at", ""),
            }
            for t in relevant
        ]

        # Haiku synthesis
        tweet_samples = "\n".join(
            f"- @{t.get('author_username', '?')}: {t.get('content_text', '')[:120]}"
            for t in relevant
        )
        description = ""
        if ANTHROPIC_API_KEY:
            try:
                description = haiku_classify(f"""The ASTS community sentiment has shifted {direction} over the last 7 days.
7-day score: {score_7d:+.2f} (bull={counts_7d['bullish']}, bear={counts_7d['bearish']})
30-day baseline: {score_30d:+.2f}

Representative tweets:
{tweet_samples}

Write a 2-sentence intelligence briefing about this sentiment shift. Be specific about what's driving it. No hedging.""")
            except Exception as e:
                log(f"  Haiku error: {e}")
                description = f"Community sentiment shifted {direction} ({delta:+.2f} vs 30d baseline). {len(tweets_7d)} tweets in 7d, {counts_7d['bullish']} bullish, {counts_7d['bearish']} bearish."

        today = now.strftime("%Y-%m-%d")
        sig = {
            "signal_type": "sentiment_shift",
            "severity": severity,
            "title": f"Community sentiment shifted {direction} ({delta:+.2f} vs 30d baseline)",
            "description": description,
            "source_refs": source_refs,
            "metrics": {
                "score_7d": round(score_7d, 3),
                "score_30d": round(score_30d, 3),
                "delta": round(delta, 3),
                "tweets_7d": len(tweets_7d),
                "tweets_30d": len(tweets_30d),
                "counts_7d": counts_7d,
            },
            "fingerprint": fingerprint("sentiment_shift", today, direction),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=7)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    return signals


# ── Detector 2: Filing Cluster ──────────────────────────────────────

def detect_filing_clusters(dry_run: bool = False) -> List[Dict]:
    """Multiple SEC or FCC filings in a short window = something happening."""
    log("Scanning: Filing clusters...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)
    d48h = utc_iso(now - timedelta(hours=48))
    d7 = utc_iso(now - timedelta(days=7))

    # SEC filings in last 48h
    sec_recent = supabase_request(
        "GET",
        f"filings?select=form,filing_date,summary,url,accession_number"
        f"&filing_date=gte.{d48h[:10]}&order=filing_date.desc&limit=20"
    ) or []

    # FCC filings in last 7d
    fcc_recent = supabase_request(
        "GET",
        f"fcc_filings?select=title,filed_date,filing_type,file_number,ai_summary,source_url"
        f"&filed_date=gte.{d7[:10]}&order=filed_date.desc&limit=20"
    ) or []

    # SEC cluster: 2+ filings in 48h is unusual
    if len(sec_recent) >= 2:
        forms = [f.get("form", "?") for f in sec_recent]
        source_refs = [
            {
                "table": "filings",
                "id": f.get("accession_number", ""),
                "title": f"{f.get('form', '?')} — {f.get('filing_date', '')}",
                "date": f.get("filing_date", ""),
            }
            for f in sec_recent
        ]

        description = ""
        if ANTHROPIC_API_KEY:
            filing_list = "\n".join(
                f"- {f.get('form', '?')} ({f.get('filing_date', '')}): {(f.get('summary', '') or '')[:150]}"
                for f in sec_recent
            )
            try:
                description = haiku_classify(f"""AST SpaceMobile filed {len(sec_recent)} SEC documents in the last 48 hours:
{filing_list}

Write a 2-sentence intelligence briefing about what this filing cluster might signal. Be specific about what forms were filed and what they typically indicate.""")
            except Exception as e:
                log(f"  Haiku error: {e}")

        today = now.strftime("%Y-%m-%d")
        sig = {
            "signal_type": "filing_cluster",
            "severity": "high" if len(sec_recent) >= 3 else "medium",
            "title": f"{len(sec_recent)} SEC filings in 48h: {', '.join(forms)}",
            "description": description or f"AST SpaceMobile filed {len(sec_recent)} documents ({', '.join(forms)}) in the last 48 hours.",
            "source_refs": source_refs,
            "metrics": {"filing_count": len(sec_recent), "forms": forms, "window_hours": 48},
            "fingerprint": fingerprint("filing_cluster_sec", today),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=3)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    # FCC cluster: 3+ in a week
    if len(fcc_recent) >= 3:
        types = [f.get("filing_type", "?") for f in fcc_recent]
        source_refs = [
            {
                "table": "fcc_filings",
                "id": f.get("file_number", ""),
                "title": f.get("title", "")[:80],
                "date": f.get("filed_date", ""),
            }
            for f in fcc_recent
        ]

        today = now.strftime("%Y-%m-%d")
        sig = {
            "signal_type": "filing_cluster",
            "severity": "medium",
            "title": f"{len(fcc_recent)} FCC filings in 7d: {', '.join(set(types))}",
            "description": f"AST SpaceMobile filed {len(fcc_recent)} FCC documents in the past week. Types: {', '.join(set(types))}.",
            "source_refs": source_refs,
            "metrics": {"filing_count": len(fcc_recent), "types": list(set(types)), "window_days": 7},
            "fingerprint": fingerprint("filing_cluster_fcc", today),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=3)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    if not signals:
        log(f"  No clusters ({len(sec_recent)} SEC in 48h, {len(fcc_recent)} FCC in 7d)")

    return signals


# ── Detector 3: FCC Status Changes ──────────────────────────────────

def detect_fcc_changes(dry_run: bool = False) -> List[Dict]:
    """New FCC grants, STA approvals, or status transitions."""
    log("Scanning: FCC status changes...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)
    d7 = utc_iso(now - timedelta(days=7))

    # Recently granted filings
    grants = supabase_request(
        "GET",
        f"fcc_filings?select=title,file_number,filing_type,grant_date,ai_summary,source_url"
        f"&grant_date=gte.{d7[:10]}&order=grant_date.desc&limit=10"
    ) or []

    for g in grants:
        title = g.get("title", "Unknown filing")
        file_num = g.get("file_number", "")
        ftype = g.get("filing_type", "")

        severity = "high" if ftype in ("License", "STA") else "medium"
        today = now.strftime("%Y-%m-%d")
        sig = {
            "signal_type": "fcc_status_change",
            "severity": severity,
            "title": f"FCC {ftype} granted: {title[:70]}",
            "description": g.get("ai_summary", "") or f"FCC granted {ftype} filing {file_num}: {title}",
            "source_refs": [{
                "table": "fcc_filings",
                "id": file_num,
                "title": title[:80],
                "date": g.get("grant_date", ""),
            }],
            "metrics": {"filing_type": ftype, "file_number": file_num},
            "fingerprint": fingerprint("fcc_grant", file_num),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=14)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    if not signals:
        log(f"  No new FCC grants in 7d")

    return signals


# ── Detector 4: Cross-Source Correlation ────────────────────────────

def detect_cross_source(dry_run: bool = False) -> List[Dict]:
    """Detect when a filing drops and X sentiment spikes around the same time."""
    log("Scanning: Cross-source correlations...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)
    d3 = utc_iso(now - timedelta(days=3))

    # Recent high-signal filings or PRs
    sec_recent = supabase_request(
        "GET",
        f"filings?select=form,filing_date,summary,accession_number,url"
        f"&filing_date=gte.{d3[:10]}&is_high_signal=eq.true&order=filing_date.desc&limit=5"
    ) or []

    pr_recent = supabase_request(
        "GET",
        f"press_releases?select=title,published_at,source_id,url,summary,category"
        f"&published_at=gte.{d3}&order=published_at.desc&limit=5"
    ) or []

    # For each recent filing/PR, check if there's a spike in X activity
    for filing in sec_recent + pr_recent:
        is_sec = "form" in filing
        event_date = filing.get("filing_date", filing.get("published_at", ""))[:10]
        if not event_date:
            continue

        # Count tweets mentioning ASTS around this date (1 day window)
        next_day = (datetime.fromisoformat(event_date) + timedelta(days=1)).strftime("%Y-%m-%d")
        tweets_around = supabase_request(
            "GET",
            f"x_posts?select=id,sentiment,author_username&published_at=gte.{event_date}T00:00:00Z"
            f"&published_at=lte.{next_day}T23:59:59Z&limit=200"
        ) or []

        # Also get baseline: avg tweets per day over 14d
        d14 = (datetime.fromisoformat(event_date) - timedelta(days=14)).strftime("%Y-%m-%d")
        baseline_tweets = supabase_paginate(
            f"x_posts?select=id&published_at=gte.{d14}T00:00:00Z&published_at=lte.{event_date}T00:00:00Z"
        )
        daily_baseline = len(baseline_tweets) / 14 if baseline_tweets else 0

        if daily_baseline > 0 and len(tweets_around) > daily_baseline * 2.5:
            event_title = filing.get("form", "") or filing.get("title", "")
            spike_ratio = len(tweets_around) / daily_baseline

            source_refs = [{
                "table": "filings" if is_sec else "press_releases",
                "id": filing.get("accession_number", filing.get("source_id", "")),
                "title": f"{filing.get('form', '')} {event_date}" if is_sec else filing.get("title", "")[:80],
                "date": event_date,
            }]

            # Get sentiment breakdown of the spike
            sentiments = {}
            for t in tweets_around:
                s = t.get("sentiment", "neutral")
                sentiments[s] = sentiments.get(s, 0) + 1

            description = ""
            if ANTHROPIC_API_KEY:
                try:
                    description = haiku_classify(f"""A filing/announcement dropped and X activity spiked:

Event: {event_title} on {event_date}
Summary: {(filing.get('summary', '') or '')[:300]}

X activity: {len(tweets_around)} tweets (vs {daily_baseline:.0f}/day baseline, {spike_ratio:.1f}x spike)
Sentiment: {sentiments}

Write a 2-sentence intelligence briefing about this cross-source event. What happened and how did the community react?""")
                except Exception as e:
                    log(f"  Haiku error: {e}")

            today = now.strftime("%Y-%m-%d")
            sig = {
                "signal_type": "cross_source",
                "severity": "high" if spike_ratio > 4 else "medium",
                "title": f"X activity spiked {spike_ratio:.1f}x after {event_title[:50]}",
                "description": description or f"{len(tweets_around)} tweets ({spike_ratio:.1f}x baseline) after {event_title}. Sentiment: {sentiments}",
                "source_refs": source_refs,
                "metrics": {
                    "tweet_count": len(tweets_around),
                    "daily_baseline": round(daily_baseline, 1),
                    "spike_ratio": round(spike_ratio, 1),
                    "sentiment_breakdown": sentiments,
                },
                "fingerprint": fingerprint("cross_source", event_date, event_title[:30]),
                "detected_at": utc_iso(now),
                "expires_at": utc_iso(now + timedelta(days=7)),
            }
            if store_signal(sig, dry_run):
                signals.append(sig)
                log(f"  SIGNAL: {sig['title']}")

    if not signals:
        log(f"  No cross-source correlations detected")

    return signals


# ── Detector 5: Short Interest Movement ─────────────────────────────

def detect_short_interest(dry_run: bool = False) -> List[Dict]:
    """Flag significant changes in short interest."""
    log("Scanning: Short interest...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)

    # Get latest 2 reports
    reports = supabase_request(
        "GET",
        "short_interest?select=*&symbol=eq.ASTS&order=report_date.desc&limit=2"
    ) or []

    if len(reports) < 2:
        log(f"  Need 2+ reports, have {len(reports)} — skipping")
        return signals

    latest = reports[0]
    prior = reports[1]

    shares_now = latest.get("shares_short", 0) or 0
    shares_prior = prior.get("shares_short", 0) or 0
    pct_float_now = latest.get("short_pct_float", 0) or 0

    if shares_prior == 0:
        return signals

    change_pct = ((shares_now - shares_prior) / shares_prior) * 100

    log(f"  Latest: {shares_now:,} shares ({pct_float_now}% float), prior: {shares_prior:,}")
    log(f"  Change: {change_pct:+.1f}%")

    # Threshold: >10% change
    if abs(change_pct) >= 10:
        direction = "increased" if change_pct > 0 else "decreased"
        severity = "high" if abs(change_pct) >= 20 else "medium"

        sig = {
            "signal_type": "short_interest_spike",
            "severity": severity,
            "title": f"Short interest {direction} {abs(change_pct):.0f}% ({pct_float_now}% of float)",
            "description": f"ASTS short interest {direction} from {shares_prior:,} to {shares_now:,} shares ({change_pct:+.1f}%), now {pct_float_now}% of float.",
            "source_refs": [{
                "table": "short_interest",
                "title": f"Report {latest.get('report_date', '')}",
                "date": latest.get("report_date", ""),
            }],
            "metrics": {
                "shares_short": shares_now,
                "shares_short_prior": shares_prior,
                "change_pct": round(change_pct, 1),
                "pct_float": pct_float_now,
            },
            "fingerprint": fingerprint("short_interest", latest.get("report_date", "")),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=14)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    if not signals:
        log(f"  No significant change ({change_pct:+.1f}%)")

    return signals


# ── Detector 6: New High-Signal Content ─────────────────────────────

def detect_new_content(dry_run: bool = False) -> List[Dict]:
    """Flag new press releases or high-signal filings that dropped since last scan."""
    log("Scanning: New high-signal content...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)
    d24h = utc_iso(now - timedelta(hours=24))

    # New press releases
    prs = supabase_request(
        "GET",
        f"press_releases?select=title,published_at,source_id,url,summary,category"
        f"&created_at=gte.{d24h}&order=published_at.desc&limit=10"
    ) or []

    for pr in prs:
        category = pr.get("category", "general")
        severity = "high" if category in ("satellite_launch", "partnership", "defense", "regulatory") else "medium"
        if category in ("general",):
            severity = "low"

        sig = {
            "signal_type": "new_content",
            "severity": severity,
            "title": f"New PR: {pr.get('title', '')[:70]}",
            "description": pr.get("summary", "") or pr.get("title", ""),
            "source_refs": [{
                "table": "press_releases",
                "id": pr.get("source_id", ""),
                "title": pr.get("title", "")[:80],
                "date": pr.get("published_at", ""),
            }],
            "metrics": {"category": category},
            "fingerprint": fingerprint("new_pr", pr.get("source_id", "")),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=3)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    # New high-signal SEC filings
    filings = supabase_request(
        "GET",
        f"filings?select=form,filing_date,summary,accession_number,url"
        f"&created_at=gte.{d24h}&is_high_signal=eq.true&order=filing_date.desc&limit=10"
    ) or []

    for f in filings:
        form = f.get("form", "?")
        severity = "critical" if form in ("8-K",) else "high" if form in ("10-K", "10-Q", "S-1") else "medium"

        sig = {
            "signal_type": "new_content",
            "severity": severity,
            "title": f"New SEC {form}: {(f.get('summary', '') or form)[:60]}",
            "description": f.get("summary", "") or f"New {form} filing dated {f.get('filing_date', '')}",
            "source_refs": [{
                "table": "filings",
                "id": f.get("accession_number", ""),
                "title": f"{form} — {f.get('filing_date', '')}",
                "date": f.get("filing_date", ""),
            }],
            "metrics": {"form": form},
            "fingerprint": fingerprint("new_filing", f.get("accession_number", "")),
            "detected_at": utc_iso(now),
            "expires_at": utc_iso(now + timedelta(days=7)),
        }
        if store_signal(sig, dry_run):
            signals.append(sig)
            log(f"  SIGNAL: {sig['title']}")

    if not signals:
        log(f"  No new high-signal content in 24h")

    return signals


# ── Detector 7: Patent↔Regulatory Cross-References ──────────────

def detect_patent_crossrefs(dry_run: bool = False) -> List[Dict]:
    """Find patents whose technology is referenced in recent FCC/SEC filings.
    Ported from /intel client-side cross-reference computation."""
    log("Scanning: Patent↔Regulatory cross-references...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)
    d30 = utc_iso(now - timedelta(days=30))

    # Get recent patents (last 90d or latest 20)
    patents = supabase_request(
        "GET",
        "patents?select=patent_number,title,abstract,filing_date"
        "&order=filing_date.desc&limit=20"
    ) or []

    if not patents:
        log("  No patents found — skipping")
        return signals

    # Get recent FCC filings
    fcc_recent = supabase_request(
        "GET",
        f"fcc_filings?select=title,file_number,filing_type,filed_date,ai_summary"
        f"&filed_date=gte.{d30[:10]}&order=filed_date.desc&limit=30"
    ) or []

    # Get recent SEC filings
    sec_recent = supabase_request(
        "GET",
        f"filings?select=form,filing_date,summary,accession_number"
        f"&filing_date=gte.{d30[:10]}&order=filing_date.desc&limit=20"
    ) or []

    if not fcc_recent and not sec_recent:
        log("  No recent filings to cross-reference — skipping")
        return signals

    # Extract key technology terms from patent titles/abstracts
    patent_terms: Dict[str, Dict] = {}
    for p in patents:
        title = (p.get("title") or "").lower()
        abstract = (p.get("abstract") or "").lower()
        # Key technology keywords that would indicate patent↔filing connection
        tech_keywords = []
        for kw in ["antenna", "beamforming", "phased array", "direct-to-cell",
                    "direct to cell", "d2c", "spectrum", "mimo", "unfold",
                    "deployment", "satellite constellation", "bluebird",
                    "low earth orbit", "terrestrial", "cellular", "handset"]:
            if kw in title or kw in abstract:
                tech_keywords.append(kw)
        if tech_keywords:
            patent_terms[p.get("patent_number", "")] = {
                "patent": p,
                "keywords": tech_keywords,
            }

    if not patent_terms:
        log("  No technology keywords extracted from patents — skipping")
        return signals

    # Check each recent filing for patent technology overlap
    matches_found = 0
    for filing in fcc_recent + sec_recent:
        is_sec = "form" in filing
        filing_text = (
            (filing.get("title") or "") + " " +
            (filing.get("ai_summary") or filing.get("summary") or "")
        ).lower()

        for pat_num, pat_info in patent_terms.items():
            overlap = [kw for kw in pat_info["keywords"] if kw in filing_text]
            if len(overlap) >= 2:  # Need 2+ keyword overlaps
                matches_found += 1
                pat = pat_info["patent"]
                filing_title = filing.get("form", "") or filing.get("title", "")
                filing_id = filing.get("accession_number", filing.get("file_number", ""))
                filing_date = filing.get("filing_date", filing.get("filed_date", ""))

                description = ""
                if ANTHROPIC_API_KEY and matches_found <= 3:  # Limit API calls
                    try:
                        description = haiku_classify(f"""A patent and a regulatory filing reference the same technology:

Patent: {pat.get('title', '')}
Patent #: {pat_num}
Technology keywords: {', '.join(overlap)}

Filing: {filing_title} ({filing_date})
Filing summary: {(filing.get('ai_summary') or filing.get('summary') or '')[:300]}

Write a 2-sentence intelligence briefing. What's the technology link and why does it matter for ASTS commercialization?""")
                    except Exception as e:
                        log(f"  Haiku error: {e}")

                sig = {
                    "signal_type": "patent_regulatory_crossref",
                    "severity": "high" if len(overlap) >= 3 else "medium",
                    "title": f"Patent↔Filing link: {', '.join(overlap[:3])} ({pat_num[:20]})",
                    "description": description or f"Patent {pat_num} ({pat.get('title', '')[:60]}) shares technology terms ({', '.join(overlap)}) with {filing_title}.",
                    "source_refs": [
                        {
                            "table": "patents",
                            "id": pat_num,
                            "title": pat.get("title", "")[:80],
                            "date": pat.get("filing_date", ""),
                        },
                        {
                            "table": "filings" if is_sec else "fcc_filings",
                            "id": filing_id,
                            "title": f"{filing_title[:60]}",
                            "date": filing_date,
                        },
                    ],
                    "metrics": {
                        "overlap_keywords": overlap,
                        "overlap_count": len(overlap),
                        "patent_number": pat_num,
                    },
                    "fingerprint": fingerprint("patent_crossref", pat_num, filing_id),
                    "detected_at": utc_iso(now),
                    "expires_at": utc_iso(now + timedelta(days=14)),
                }
                if store_signal(sig, dry_run):
                    signals.append(sig)
                    log(f"  SIGNAL: {sig['title']}")

                if len(signals) >= 5:  # Cap at 5 cross-ref signals per scan
                    break
        if len(signals) >= 5:
            break

    if not signals:
        log(f"  No patent↔filing cross-references detected")

    return signals


# ── Detector 8: Earnings Language Shift ──────────────────────────

def detect_earnings_shifts(dry_run: bool = False) -> List[Dict]:
    """Compare most recent two earnings transcripts for significant language changes.
    Ported from /intel client-side earnings diff computation."""
    log("Scanning: Earnings language shifts...")
    signals: List[Dict] = []

    now = datetime.now(timezone.utc)

    # Get latest 2 transcripts
    transcripts = supabase_request(
        "GET",
        "earnings_transcripts?select=company,fiscal_year,fiscal_quarter,content_text,published_at"
        "&company=eq.ASTS&order=published_at.desc&limit=2"
    ) or []

    if len(transcripts) < 2:
        log(f"  Need 2+ transcripts, have {len(transcripts)} — skipping")
        return signals

    current = transcripts[0]
    previous = transcripts[1]

    current_text = (current.get("content_text") or "")[:5000]
    previous_text = (previous.get("content_text") or "")[:5000]

    if not current_text or not previous_text:
        log("  Transcripts missing content — skipping")
        return signals

    current_label = f"Q{current.get('fiscal_quarter', '?')} {current.get('fiscal_year', '?')}"
    previous_label = f"Q{previous.get('fiscal_quarter', '?')} {previous.get('fiscal_year', '?')}"

    # Use Haiku to identify language shifts
    if not ANTHROPIC_API_KEY:
        log("  No ANTHROPIC_API_KEY — skipping language analysis")
        return signals

    try:
        analysis = haiku_classify(f"""Compare these two ASTS earnings call transcripts for significant language shifts.

PREVIOUS ({previous_label}):
{previous_text[:2500]}

CURRENT ({current_label}):
{current_text[:2500]}

Identify the top 3 most significant changes in language, terminology, or emphasis between these calls.
Format as JSON array: [{{"topic": "...", "direction": "new|dropped|shifted", "detail": "..."}}]
Only include genuinely significant shifts, not routine changes. Return empty array [] if nothing notable.""", max_tokens=800)

        # Parse the response
        shifts = []
        try:
            # Extract JSON from response
            json_start = analysis.find("[")
            json_end = analysis.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                shifts = json.loads(analysis[json_start:json_end])
        except (json.JSONDecodeError, ValueError):
            log(f"  Could not parse Haiku response as JSON")

        if shifts and len(shifts) > 0:
            shift_summary = "; ".join(
                f"{s.get('topic', '?')} ({s.get('direction', '?')})"
                for s in shifts[:3]
            )

            description = ""
            try:
                description = haiku_classify(f"""The ASTS earnings call language shifted from {previous_label} to {current_label}:

Shifts detected:
{json.dumps(shifts[:3], indent=2)}

Write a 2-sentence intelligence briefing about what these language changes signal for ASTS. Be specific and actionable.""")
            except Exception:
                pass

            sig = {
                "signal_type": "earnings_language_shift",
                "severity": "high" if len(shifts) >= 3 else "medium",
                "title": f"Earnings language shift: {current_label} vs {previous_label}",
                "description": description or f"Language shifts detected between {previous_label} and {current_label}: {shift_summary}",
                "source_refs": [
                    {
                        "table": "earnings_transcripts",
                        "title": f"{current_label} Earnings Call",
                        "date": current.get("published_at", ""),
                    },
                    {
                        "table": "earnings_transcripts",
                        "title": f"{previous_label} Earnings Call",
                        "date": previous.get("published_at", ""),
                    },
                ],
                "metrics": {
                    "shifts": shifts[:3],
                    "shift_count": len(shifts),
                    "current_quarter": current_label,
                    "previous_quarter": previous_label,
                },
                "fingerprint": fingerprint("earnings_shift", current_label, previous_label),
                "detected_at": utc_iso(now),
                "expires_at": utc_iso(now + timedelta(days=90)),
            }
            if store_signal(sig, dry_run):
                signals.append(sig)
                log(f"  SIGNAL: {sig['title']}")
        else:
            log(f"  No significant language shifts between {previous_label} and {current_label}")

    except Exception as e:
        log(f"  Error in earnings analysis: {e}")

    return signals


# ── Main ─────────────────────────────────────────────────────────────

def run_scanner():
    parser = argparse.ArgumentParser(description="Signal Scanner — Cross-Source Anomaly Detection")
    parser.add_argument("--dry-run", action="store_true", help="Detect signals but don't store")
    parser.add_argument("--detector", type=str, help="Run a single detector (sentiment, filing, fcc, cross, short, content)")
    args = parser.parse_args()

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    log("=" * 60)
    log("SIGNAL SCANNER v2")
    log("=" * 60)

    detectors = {
        "sentiment": detect_sentiment_shifts,
        "filing": detect_filing_clusters,
        "fcc": detect_fcc_changes,
        "cross": detect_cross_source,
        "short": detect_short_interest,
        "content": detect_new_content,
        "patent_crossref": detect_patent_crossrefs,
        "earnings": detect_earnings_shifts,
    }

    if args.detector:
        if args.detector not in detectors:
            log(f"ERROR: Unknown detector '{args.detector}'. Options: {', '.join(detectors.keys())}")
            sys.exit(1)
        run_list = {args.detector: detectors[args.detector]}
    else:
        run_list = detectors

    all_signals: List[Dict] = []
    for name, detector in run_list.items():
        try:
            signals = detector(dry_run=args.dry_run)
            all_signals.extend(signals)
        except Exception as e:
            log(f"  ERROR in {name} detector: {e}")

    log("")
    log("=" * 60)
    log(f"SCAN COMPLETE: {len(all_signals)} signals detected")
    for sig in all_signals:
        log(f"  [{sig['severity'].upper()}] {sig['title']}")
    log("=" * 60)


if __name__ == "__main__":
    run_scanner()
