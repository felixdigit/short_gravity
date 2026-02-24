#!/usr/bin/env python3
"""
X/Twitter Worker — ASTS Intelligence Pipeline

Pulls timelines from tracked accounts, filters by keyword, classifies with Haiku.

Run:
  cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 x_worker.py
  cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 x_worker.py --dry-run

Schedule: GitHub Actions cron (see .github/workflows/x-worker.yml)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple


# ── Configuration ────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")

# Tracked accounts — primary data source
# filter: keyword that must appear in tweet text (case-insensitive), or None for all tweets
TRACKED_ACCOUNTS = [
    {"username": "AST_SpaceMobile", "filter": None},
    {"username": "thekookreport", "filter": None},
    {"username": "CatSE___ApeX___", "filter": None},
    {"username": "Defiantclient2", "filter": "$ASTS OR ASTS OR AST"},
    {"username": "jusbar23", "filter": "$ASTS OR ASTS OR AST"},
]


# Tweet fields to request
TWEET_FIELDS = "author_id,conversation_id,created_at,in_reply_to_user_id,public_metrics,referenced_tweets,attachments,note_tweet,entities"
USER_FIELDS = "username,name"
MEDIA_FIELDS = "media_key,type,url,preview_image_url,alt_text,width,height,variants"
EXPANSIONS = "author_id,referenced_tweets.id,attachments.media_keys"



# ── Helpers ──────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None):
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


def x_api_request(url: str, params: Optional[Dict] = None) -> Tuple[Optional[Dict], Dict]:
    """Make authenticated X API request. Returns (data, headers)."""
    if params:
        query_string = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query_string}"

    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {X_BEARER_TOKEN}",
        "User-Agent": "ShortGravityBot/1.0",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            headers = {k.lower(): v for k, v in response.getheaders()}
            content = response.read().decode("utf-8")
            return json.loads(content) if content else None, headers
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited — read reset header
            reset_time = e.headers.get("x-rate-limit-reset")
            if reset_time:
                wait_seconds = int(reset_time) - int(time.time()) + 1
                if wait_seconds > 0:
                    log(f"  Rate limited. Sleeping {wait_seconds}s until reset...")
                    time.sleep(wait_seconds)
                    return x_api_request(url)  # Retry (url already has params)
            else:
                log("  Rate limited (no reset header). Sleeping 60s...")
                time.sleep(60)
                return x_api_request(url)
        error_body = e.read().decode("utf-8")
        log(f"X API error: {e.code} - {error_body}")
        return None, {}


def get_existing_ids() -> set:
    """Fetch all existing source_ids, paginating past Supabase 1000-row default."""
    all_ids = set()
    offset = 0
    batch = 1000
    try:
        while True:
            result = supabase_request("GET", f"x_posts?select=source_id&limit={batch}&offset={offset}")
            if not result:
                break
            all_ids.update(r["source_id"] for r in result)
            if len(result) < batch:
                break
            offset += batch
        return all_ids
    except Exception as e:
        log(f"Error fetching existing: {e}")
        return all_ids


def get_latest_tweet_id(username: Optional[str] = None) -> Optional[str]:
    """Get the most recent tweet_id for incremental monitor mode."""
    try:
        query = "x_posts?select=tweet_id&order=published_at.desc&limit=1"
        if username:
            query += f"&author_username=eq.{username}"
        result = supabase_request("GET", query)
        if result and len(result) > 0:
            return result[0]["tweet_id"]
    except Exception:
        pass
    return None


def get_oldest_tweet_time(username: str) -> Optional[str]:
    """Get the oldest stored tweet timestamp for a user (for backfill resume)."""
    try:
        result = supabase_request(
            "GET",
            f"x_posts?select=published_at&author_username=eq.{username}&order=published_at.asc&limit=1"
        )
        if result and len(result) > 0:
            return result[0]["published_at"]
    except Exception:
        pass
    return None


# ── AI Classification ────────────────────────────────────────────────

def classify_tweet(text: str, author: str) -> Dict[str, Any]:
    """Classify tweet using Haiku. Falls back to rule-based."""
    if ANTHROPIC_API_KEY and len(text) > 20:
        result = _haiku_classify(text, author)
        if result:
            return result
    return _rule_classify(text, author)


def _haiku_classify(text: str, author: str) -> Optional[Dict[str, Any]]:
    """Use Claude Haiku for tweet classification."""
    prompt = f"""You are classifying tweets from the $ASTS (AST SpaceMobile) investor community for a research intelligence database. Your classifications power search, filtering, and sentiment analysis — precision matters.

CONTEXT: AST SpaceMobile is building a space-based cellular broadband network using BlueBird satellites in low Earth orbit. Key topics: satellite launches (SpaceX), FCC/ITU spectrum licensing, MNO partnerships (AT&T, Verizon, Vodafone, Rakuten), direct-to-cell (D2C) technology, BlueWalker 3 test satellite, Abel Avellan (CEO).

KNOWN VOICES:
- @AST_SpaceMobile, @AbelAvellan → official company/CEO accounts
- @CatSE___ApeX___ → deep regulatory/FCC analyst, files FOIA requests, reads FCC dockets
- @thekookreport → community analyst, tracks catalysts and sentiment
- @spacanpanman → aggregator/narrator of ASTS developments
- @Defiantclient2 → community member, engagement amplifier

Tweet by @{author}:
"{text}"

Classify into this exact JSON:
{{"sentiment":"...","signal_type":"...","category":"...","tags":[...],"summary":"..."}}

FIELD DEFINITIONS:

sentiment (investor lens — how does this affect the $ASTS thesis?):
- "bullish" → positive catalyst, progress, good news, optimism about stock/company
- "bearish" → negative catalyst, delays, risks, dilution, pessimism
- "neutral" → mixed or no clear directional impact
- "informational" → pure facts, data, filings, no opinion embedded

signal_type (what kind of intelligence is this?):
- "official" → from @AST_SpaceMobile or @AbelAvellan only
- "insider_signal" → reveals non-obvious info: FOIA results, FCC docket analysis, unreported filings, channel checks, supply chain intel
- "breaking_news" → first to report a material event (launch date, partnership, filing)
- "analyst_take" → original analysis, thesis, valuation argument, technical breakdown, regulatory interpretation, catalyst timeline. USE THIS for @CatSE___ApeX___ FCC/spectrum analysis and for any substantive opinion with reasoning
- "community" → reactions, cheerleading, memes, simple retweet commentary, engagement without original analysis

category (primary topic — pick the most specific match):
- "satellite_launch" → launches, orbits, deployment, SpaceX, BlueBird, BlueWalker, constellation status
- "spectrum" → FCC filings, spectrum licenses, ITU coordination, interference, AST-specific regulatory (NOT general telecom regulation)
- "regulatory" → non-spectrum regulatory: SEC filings, congressional, international approvals, export controls
- "partnership" → MNO deals (AT&T, Verizon, Vodafone, Rakuten), commercial agreements, revenue sharing
- "technology" → D2C tech, antenna design, network architecture, test results, throughput, latency
- "financing" → capital raises, ATM offerings, dilution, cash runway, debt
- "earnings" → quarterly results, revenue, guidance, earnings calls
- "competitive" → competitors (Lynk, SpaceX D2C, Skylo), market positioning
- "general" → only if nothing above fits

tags (extract ALL relevant entities as lowercase strings):
Include satellite names (bluebird, bluewalker 3), partners (at&t, verizon, vodafone, rakuten), people (abel avellan), agencies (fcc, itu, sec), technologies (d2c, direct-to-cell), launch providers (spacex), competitors (lynk, starlink).

summary: One sentence capturing the key intelligence value. Write it as a research note, not a tweet summary. Focus on WHAT matters and WHY.

JSON only:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw = result["content"][0]["text"].strip()
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        log(f"    Haiku classification error: {e}")
    return None


def describe_image(image_url: str) -> Optional[str]:
    """Use Haiku vision to describe an image (screenshot, chart, document)."""
    if not ANTHROPIC_API_KEY or not image_url:
        return None

    # Fetch image
    try:
        req = urllib.request.Request(image_url, headers={
            "User-Agent": "ShortGravityBot/1.0",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            if not content_type.startswith("image/"):
                return None
            image_data = resp.read()
            if len(image_data) > 5_000_000:  # Skip >5MB
                return None
            import base64
            b64 = base64.b64encode(image_data).decode()
    except Exception as e:
        log(f"    Image fetch failed: {e}")
        return None

    # Vision call
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": content_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": "Describe this image concisely for a research database. If it's a document, filing, chart, or screenshot, extract the key text/data. If it's a photo, describe what's shown. Focus on factual content. 2-3 sentences max.",
                },
            ],
        }],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"    Vision describe failed: {e}")
        return None


def is_thin_content(text: str) -> bool:
    """Check if tweet text is too thin to be useful (mostly links/short)."""
    stripped = re.sub(r'https?://\S+', '', text).strip()
    # Remove media tags we added
    stripped = re.sub(r'\[(photo|video|gif)[^\]]*\]', '', stripped).strip()
    return len(stripped) < 30


def _rule_classify(text: str, author: str) -> Dict[str, Any]:
    """Rule-based fallback classification."""
    t = text.lower()
    a = author.lower().replace("_", "")

    # Sentiment
    sentiment = "neutral"
    bull_words = ["moon", "bullish", "buy", "long", "upside", "breakout", "launch success",
                  "🚀", "💎", "partnership", "deal", "revenue", "approved", "granted"]
    bear_words = ["bearish", "sell", "short", "overvalued", "dilution", "delay", "risk", "fail", "denied"]
    if any(w in t for w in bull_words):
        sentiment = "bullish"
    elif any(w in t for w in bear_words):
        sentiment = "bearish"

    # Signal type
    signal_type = "community"
    if a in ["astspacemobile", "abelavellan"]:
        signal_type = "official"
    elif a in ["catseapex"] or "foia" in t or "docket" in t:
        signal_type = "analyst_take"
    elif any(w in t for w in ["breaking", "just announced", "just filed", "confirmed"]):
        signal_type = "breaking_news"

    # Category — ordered by specificity
    category = "general"
    if any(w in t for w in ["fcc", "spectrum", "license", "itu", "mhz", "ghz", "interference", "docket"]):
        category = "spectrum"
    elif any(w in t for w in ["launch", "bluebird", "orbit", "satellite", "bluewalker", "spacex", "constellation", "deploy"]):
        category = "satellite_launch"
    elif any(w in t for w in ["partner", "at&t", "verizon", "vodafone", "rakuten", "agreement", "mno"]):
        category = "partnership"
    elif any(w in t for w in ["d2c", "direct-to-cell", "antenna", "throughput", "latency", "mbps"]):
        category = "technology"
    elif any(w in t for w in ["sec", "regulatory", "approval", "congress"]):
        category = "regulatory"
    elif any(w in t for w in ["offering", "dilution", "capital", "financing", "atm", "cash"]):
        category = "financing"
    elif any(w in t for w in ["earnings", "quarter", "q1", "q2", "q3", "q4", "revenue"]):
        category = "earnings"
    elif any(w in t for w in ["lynk", "starlink", "skylo", "competitor"]):
        category = "competitive"

    # Tags
    tags = []
    tag_map = {
        "bluebird": "bluebird", "bluewalker": "bluewalker 3", "at&t": "at&t",
        "verizon": "verizon", "vodafone": "vodafone", "rakuten": "rakuten",
        "spacex": "spacex", "fcc": "fcc", "itu": "itu", "sec": "sec",
        "direct-to-cell": "d2c", "d2c": "d2c", "abel avellan": "abel avellan",
        "lynk": "lynk", "starlink": "starlink",
    }
    for keyword, tag in tag_map.items():
        if keyword in t and tag not in tags:
            tags.append(tag)

    return {
        "sentiment": sentiment,
        "signal_type": signal_type,
        "category": category,
        "tags": tags,
        "summary": text[:140],
    }


# ── Tweet Processing ─────────────────────────────────────────────────

def parse_tweets(response_data: Dict, query: str) -> List[Dict]:
    """Parse X API v2 response into flat tweet records."""
    tweets = response_data.get("data", [])
    includes = response_data.get("includes", {})

    # Build user lookup from includes
    users = {}
    for user in includes.get("users", []):
        users[user["id"]] = {
            "username": user.get("username", ""),
            "name": user.get("name", ""),
        }

    # Build media lookup from includes
    media_map = {}
    for media in includes.get("media", []):
        media_key = media.get("media_key", "")
        media_entry = {"type": media.get("type", "")}
        if media.get("url"):
            media_entry["url"] = media["url"]
        if media.get("preview_image_url"):
            media_entry["preview_url"] = media["preview_image_url"]
        if media.get("alt_text"):
            media_entry["alt_text"] = media["alt_text"]
        if media.get("width"):
            media_entry["width"] = media["width"]
        if media.get("height"):
            media_entry["height"] = media["height"]
        # Video variants (different resolutions)
        if media.get("variants"):
            best = None
            for v in media["variants"]:
                if v.get("content_type") == "video/mp4":
                    if not best or (v.get("bit_rate", 0) > best.get("bit_rate", 0)):
                        best = v
            if best:
                media_entry["video_url"] = best["url"]
        media_map[media_key] = media_entry

    records = []
    for tweet in tweets:
        tweet_id = tweet["id"]
        author_id = tweet.get("author_id", "")
        user_info = users.get(author_id, {"username": "", "name": ""})

        # Use note_tweet text for long tweets, fall back to regular text
        note = tweet.get("note_tweet", {})
        content_text = note.get("text") or tweet.get("text", "")

        # Expand t.co URLs to real URLs using entities
        entities = tweet.get("entities", {})
        if not entities and note:
            entities = note.get("entities", {})
        for url_entity in entities.get("urls", []):
            short = url_entity.get("url", "")
            expanded = url_entity.get("expanded_url", "")
            if short and expanded and short in content_text:
                # Don't expand twitter/x.com media URLs (they're just the tweet itself)
                if not expanded.startswith(("https://twitter.com/", "https://x.com/")):
                    content_text = content_text.replace(short, expanded)
                elif "/photo/" in expanded or "/video/" in expanded:
                    # Media self-links: remove the t.co link (media is captured separately)
                    content_text = content_text.replace(short, "").strip()

        # Public metrics
        metrics = tweet.get("public_metrics", {})

        # Check if this is a reply
        in_reply_to_id = None
        is_thread_root = True
        refs = tweet.get("referenced_tweets", [])
        for ref in refs:
            if ref["type"] == "replied_to":
                in_reply_to_id = ref["id"]
                is_thread_root = False
                break

        # Collect media URLs
        media_keys = tweet.get("attachments", {}).get("media_keys", [])
        media_urls = []
        for mk in media_keys:
            if mk in media_map:
                media_urls.append(media_map[mk])

        # Append media context to content_text so it's searchable
        media_descriptions = []
        for m in media_urls:
            mtype = m.get("type", "photo")
            alt = m.get("alt_text", "")
            if alt:
                media_descriptions.append(f"[{mtype}: {alt}]")
            elif mtype == "video":
                media_descriptions.append("[video attached]")
            elif mtype == "animated_gif":
                media_descriptions.append("[gif attached]")
            # photos without alt text: don't add noise
        if media_descriptions:
            content_text = content_text.rstrip() + "\n" + " ".join(media_descriptions)

        # Published time
        created_at = tweet.get("created_at", "")

        records.append({
            "tweet_id": tweet_id,
            "author_id": author_id,
            "author_username": user_info["username"],
            "author_name": user_info["name"],
            "content_text": content_text,
            "published_at": created_at,
            "conversation_id": tweet.get("conversation_id"),
            "in_reply_to_id": in_reply_to_id,
            "in_reply_to_user_id": tweet.get("in_reply_to_user_id"),
            "is_thread_root": is_thread_root,
            "metrics": {
                "retweets": metrics.get("retweet_count", 0),
                "likes": metrics.get("like_count", 0),
                "replies": metrics.get("reply_count", 0),
                "quotes": metrics.get("quote_count", 0),
                "impressions": metrics.get("impression_count", 0),
            },
            "media": media_urls if media_urls else None,
            "search_query": query,
            "url": f"https://x.com/{user_info['username']}/status/{tweet_id}" if user_info["username"] else None,
        })

    return records


def store_tweet(record: Dict, existing_ids: set, dry_run: bool = False,
                classify: bool = True) -> str:
    """Store a single tweet. Optionally classify with Haiku. Returns: 'saved', 'skipped', or 'failed'."""
    source_id = f"x_{record['tweet_id']}"
    if source_id in existing_ids:
        return "skipped"

    # Check DB directly to catch tweets saved by previous interrupted runs
    try:
        check = supabase_request("GET", f"x_posts?select=id&source_id=eq.{source_id}&limit=1")
        if check and len(check) > 0:
            existing_ids.add(source_id)
            return "skipped"
    except Exception:
        pass

    # Enrich image-only tweets with vision descriptions
    content_text = record["content_text"]
    media = record.get("media") or []
    photos = [m for m in media if m.get("type") == "photo"]
    if photos and is_thin_content(content_text) and classify:
        photo_url = photos[0].get("url") or photos[0].get("preview_url")
        if photo_url:
            desc = describe_image(photo_url)
            if desc:
                content_text = content_text.rstrip() + f"\n[image content: {desc}]"
                record["content_text"] = content_text
                log(f"    Image described: {desc[:60]}...")

    # Classify only if requested (skip during fast scrape)
    if classify:
        classification = classify_tweet(record["content_text"], record["author_username"])
    else:
        classification = {}

    row = {
        "source_id": source_id,
        "tweet_id": record["tweet_id"],
        "author_id": record["author_id"],
        "author_username": record["author_username"],
        "author_name": record["author_name"],
        "content_text": record["content_text"],
        "published_at": record["published_at"],
        "summary": classification.get("summary"),
        "sentiment": classification.get("sentiment"),
        "signal_type": classification.get("signal_type"),
        "category": classification.get("category"),
        "tags": classification.get("tags", []),
        "metrics": {**record["metrics"], "media": record.get("media")} if record.get("media") else record["metrics"],
        "conversation_id": record.get("conversation_id"),
        "in_reply_to_id": record.get("in_reply_to_id"),
        "is_thread_root": record.get("is_thread_root", True),
        "search_query": record["search_query"],
        "url": record["url"],
    }

    if dry_run:
        log(f"    [DRY RUN] @{record['author_username']}: {record['content_text'][:80]}...")
        return "saved"

    try:
        supabase_request("POST", "x_posts", row)
        existing_ids.add(source_id)
        return "saved"
    except urllib.error.HTTPError as e:
        if e.code == 409:
            existing_ids.add(source_id)
            return "skipped"
        log(f"    Store error: {e}")
        return "failed"
    except Exception as e:
        log(f"    Store error: {e}")
        return "failed"


def classify_stored_tweets(username: Optional[str] = None, batch_size: int = 50):
    """Classify tweets already in DB that have no sentiment (unclassified). Haiku only, no X API cost."""
    query = "x_posts?select=id,content_text,author_username&sentiment=is.null&order=published_at.asc"
    if username:
        query += f"&author_username=eq.{username}"
    query += f"&limit={batch_size}"

    total = 0
    while True:
        rows = supabase_request("GET", query)
        if not rows:
            break

        for row in rows:
            classification = classify_tweet(row["content_text"], row["author_username"])
            try:
                supabase_request("PATCH", f"x_posts?id=eq.{row['id']}", {
                    "summary": classification.get("summary"),
                    "sentiment": classification.get("sentiment"),
                    "signal_type": classification.get("signal_type"),
                    "category": classification.get("category"),
                    "tags": classification.get("tags", []),
                })
                total += 1
                if total % 50 == 0:
                    log(f"    Classified {total} tweets...")
            except Exception as e:
                log(f"    Classify error on id={row['id']}: {e}")

    log(f"    Classification complete: {total} tweets classified")
    return total


# ── Run ──────────────────────────────────────────────────────────────


def _fetch_user_timeline(username: str, keyword_filter: Optional[str],
                         existing_ids: set, since_id: Optional[str],
                         dry_run: bool, max_pages: int = 0,
                         end_time: Optional[str] = None,
                         classify: bool = True) -> Tuple[int, int, int]:
    """Fetch recent tweets from a user's timeline, optionally filtering by keyword."""
    filter_label = f" (filter: {keyword_filter})" if keyword_filter else ""
    log(f"\n  Timeline: @{username}{filter_label}")
    if end_time:
        log(f"    Resuming backfill — fetching tweets before {end_time}")

    # First get user ID
    user_url = f"https://api.x.com/2/users/by/username/{username}"
    user_data, _ = x_api_request(user_url)
    if not user_data or "data" not in user_data:
        log(f"    Could not find user @{username}")
        return 0, 0, 0

    user_id = user_data["data"]["id"]
    saved = 0
    skipped = 0
    failed = 0
    filtered_out = 0
    next_token = None
    pages = 0

    while True:
        pages += 1
        if max_pages > 0 and pages > max_pages:
            log(f"    Reached max pages ({max_pages})")
            break
        # Fetch timeline page
        timeline_url = f"https://api.x.com/2/users/{user_id}/tweets"
        params: Dict[str, Any] = {
            "max_results": 100,
            "tweet.fields": TWEET_FIELDS,
            "user.fields": USER_FIELDS,
            "media.fields": MEDIA_FIELDS,
            "expansions": EXPANSIONS,
            "exclude": "retweets",
        }
        if since_id:
            params["since_id"] = since_id
        if end_time:
            params["end_time"] = end_time
        if next_token:
            params["pagination_token"] = next_token

        data, _ = x_api_request(timeline_url, params)
        if not data:
            break

        meta = data.get("meta", {})
        result_count = meta.get("result_count", 0)
        if result_count == 0:
            break

        # Inject user info into includes if not present
        includes = data.get("includes", {})
        if "users" not in includes:
            includes["users"] = []
        user_ids_in_includes = {u["id"] for u in includes.get("users", [])}
        if user_id not in user_ids_in_includes:
            includes["users"].append({
                "id": user_id,
                "username": username,
                "name": user_data["data"].get("name", username),
            })
        data["includes"] = includes

        records = parse_tweets(data, f"@{username}")
        page_saved = 0
        page_filtered = 0
        for record in records:
            # Apply keyword filter
            if keyword_filter and keyword_filter.lower() not in record["content_text"].lower():
                filtered_out += 1
                page_filtered += 1
                continue

            result = store_tweet(record, existing_ids, dry_run, classify=classify)
            if result == "saved":
                saved += 1
                page_saved += 1
            elif result == "skipped":
                skipped += 1
            else:
                failed += 1

        log(f"    p{pages}: {result_count} fetched, {page_saved} saved, {page_filtered} filtered | total: {saved} saved, {filtered_out} filtered")

        next_token = meta.get("next_token")
        if not next_token:
            log(f"    No more pages — backfill complete")
            break
        time.sleep(1)

    log(f"    @{username} DONE: {saved} saved, {skipped} skipped, {filtered_out} filtered out")
    return saved, skipped, failed


def _search_archive(username: str, user_id: str, existing_ids: set,
                     dry_run: bool, max_pages: int = 0,
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None,
                     classify: bool = True,
                     keyword_filter: Optional[str] = None) -> Tuple[int, int, int]:
    """Full archive search for a user's tweets. Stores everything (no RTs)."""
    query = f"from:{username} -is:retweet"
    if keyword_filter:
        # Wrap in parens if it contains OR to scope properly
        if " OR " in keyword_filter and not keyword_filter.startswith("("):
            query += f" ({keyword_filter})"
        else:
            query += f" {keyword_filter}"
    log(f"\n  Archive search: {query}")
    if start_time:
        log(f"    start_time: {start_time}")
    if end_time:
        log(f"    end_time: {end_time}")
    if not classify:
        log(f"    Fast scrape mode — no classification")

    saved = 0
    skipped = 0
    failed = 0
    next_token = None
    pages = 0

    while True:
        pages += 1
        if max_pages > 0 and pages > max_pages:
            log(f"    Reached max pages ({max_pages})")
            break

        url = "https://api.x.com/2/tweets/search/all"
        params: Dict[str, Any] = {
            "query": query,
            "max_results": 500,
            "tweet.fields": TWEET_FIELDS,
            "user.fields": USER_FIELDS,
            "media.fields": MEDIA_FIELDS,
            "expansions": EXPANSIONS,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if next_token:
            params["next_token"] = next_token

        data, _ = x_api_request(url, params)
        if not data:
            break

        meta = data.get("meta", {})
        result_count = meta.get("result_count", 0)
        if result_count == 0:
            break

        records = parse_tweets(data, f"search:@{username}")
        page_saved = 0
        for record in records:
            result = store_tweet(record, existing_ids, dry_run, classify=classify)
            if result == "saved":
                saved += 1
                page_saved += 1
            elif result == "skipped":
                skipped += 1
            else:
                failed += 1

        log(f"    p{pages}: {result_count} fetched, {page_saved} saved | total: {saved} saved, {skipped} skipped")

        next_token = meta.get("next_token")
        if not next_token:
            log(f"    No more pages — archive search complete")
            break
        time.sleep(1)

    log(f"    @{username} DONE: {saved} saved, {skipped} skipped")
    return saved, skipped, failed


# ── Main ─────────────────────────────────────────────────────────────

def run_worker():
    parser = argparse.ArgumentParser(description="X/Twitter ASTS Intelligence Worker")
    parser.add_argument("--dry-run", action="store_true", help="Parse and classify but don't store")
    parser.add_argument("--account", type=str, help="Target a single account username")
    parser.add_argument("--backfill", action="store_true", help="Full history (ignore since_id)")
    parser.add_argument("--max-pages", type=int, default=0, help="Max pages per account (0=unlimited)")
    parser.add_argument("--no-resume", action="store_true", help="Backfill from scratch (don't skip to oldest stored)")
    parser.add_argument("--search", action="store_true", help="Use full archive search instead of timeline (deeper history)")
    parser.add_argument("--end-time", type=str, help="Only fetch tweets before this ISO timestamp")
    parser.add_argument("--start-time", type=str, help="Only fetch tweets after this ISO timestamp")
    parser.add_argument("--no-classify", action="store_true", help="Fast scrape — store raw, skip Haiku classification")
    parser.add_argument("--classify-only", action="store_true", help="Classify unclassified tweets in DB (no X API cost)")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    # Classify-only mode — no X API needed
    if args.classify_only:
        if not ANTHROPIC_API_KEY:
            log("ERROR: ANTHROPIC_API_KEY not set")
            sys.exit(1)
        log("=" * 60)
        log(f"X WORKER v1 — CLASSIFY ONLY")
        if args.account:
            log(f"  Account: @{args.account}")
        log("=" * 60)
        classify_stored_tweets(username=args.account)
        return

    # Determine which accounts to run
    if args.account:
        accounts = [a for a in TRACKED_ACCOUNTS if a["username"].lower() == args.account.lower()]
        if not accounts:
            log(f"ERROR: Account @{args.account} not in TRACKED_ACCOUNTS")
            sys.exit(1)
    else:
        accounts = TRACKED_ACCOUNTS

    classify = not args.no_classify
    mode = "ARCHIVE SEARCH" if args.search else ("BACKFILL" if args.backfill else "MONITOR")
    if not classify:
        mode += " (fast scrape)"
    log("=" * 60)
    log(f"X WORKER v1 — {mode}")
    log(f"  Accounts: {', '.join('@' + a['username'] for a in accounts)}")
    if args.max_pages:
        log(f"  Max pages: {args.max_pages}")
    log("=" * 60)

    if not X_BEARER_TOKEN:
        log("ERROR: X_BEARER_TOKEN not set")
        sys.exit(1)

    existing_ids = get_existing_ids()
    log(f"Existing tweets in DB: {len(existing_ids)}")

    total_saved = 0
    total_skipped = 0
    total_failed = 0

    for account in accounts:
        username = account["username"]

        if args.search:
            # Full archive search — resolve user ID first
            user_url = f"https://api.x.com/2/users/by/username/{username}"
            user_data, _ = x_api_request(user_url)
            if not user_data or "data" not in user_data:
                log(f"  Could not find user @{username}")
                continue
            user_id = user_data["data"]["id"]

            # Auto-resume: use oldest stored tweet as end_time if not specified
            end_time = args.end_time
            if not end_time and not args.no_resume:
                oldest = get_oldest_tweet_time(username)
                if oldest:
                    end_time = oldest
                    log(f"  Resuming @{username} archive search before {oldest}")

            saved, skipped, failed = _search_archive(
                username, user_id, existing_ids,
                args.dry_run, args.max_pages,
                start_time=args.start_time, end_time=end_time,
                classify=classify,
                keyword_filter=account.get("filter")
            )
        else:
            # Timeline mode
            since_id = None if args.backfill else get_latest_tweet_id(username)
            if since_id:
                log(f"Fetching since tweet_id: {since_id}")

            end_time = None
            if args.backfill and not args.no_resume:
                oldest = get_oldest_tweet_time(username)
                if oldest:
                    end_time = oldest
                    log(f"  Resuming @{username} backfill from {oldest}")

            saved, skipped, failed = _fetch_user_timeline(
                username, account.get("filter"),
                existing_ids, since_id, args.dry_run, args.max_pages,
                end_time=end_time, classify=classify
            )

        total_saved += saved
        total_skipped += skipped
        total_failed += failed

    log("=" * 60)
    log(f"DONE: {total_saved} saved, {total_skipped} skipped, {total_failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
