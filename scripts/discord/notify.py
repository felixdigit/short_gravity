"""
Short Gravity — Discord Notification Utility

Shared module for all workers to send Discord webhook notifications.
Import and call send() after inserting new data into Supabase.

Usage:
    from discord.notify import send, Channel

    send(Channel.SEC_FILINGS, embed={
        "title": "New 8-K Filing",
        "description": "AST SpaceMobile filed an 8-K on 2026-02-09",
        "url": "https://sec.gov/...",
        "color": 0xFF6B35,
    })
"""

from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.error
from enum import Enum
from typing import Optional


class Channel(Enum):
    SEC_FILINGS = "DISCORD_WEBHOOK_SEC"
    FCC_REGULATORY = "DISCORD_WEBHOOK_FCC"
    PATENTS = "DISCORD_WEBHOOK_PATENTS"
    PRESS_RELEASES = "DISCORD_WEBHOOK_PRESS"
    LAUNCHES = "DISCORD_WEBHOOK_LAUNCHES"
    EARNINGS = "DISCORD_WEBHOOK_EARNINGS"
    ORBITAL_OPS = "DISCORD_WEBHOOK_ORBITAL"
    SIGNALS = "DISCORD_WEBHOOK_SIGNALS"
    BOT_LOG = "DISCORD_WEBHOOK_BOT_LOG"


# Short Gravity orange
BRAND_COLOR = 0xFF6B35
BRAND_ICON = "https://shortgravity.com/favicon.ico"


def send(
    channel: Channel,
    content: Optional[str] = None,
    embed: Optional[dict] = None,
    silent: bool = False,
) -> bool:
    """
    Send a Discord notification via webhook.

    Args:
        channel: Target channel (maps to env var for webhook URL)
        content: Plain text message (optional if embed provided)
        embed: Discord embed dict (title, description, url, color, fields, etc.)
        silent: If True, suppress errors (useful for non-critical notifications)

    Returns:
        True if sent successfully, False otherwise
    """
    webhook_url = os.environ.get(channel.value)
    if not webhook_url:
        if not silent:
            print(f"[discord] No webhook URL for {channel.value} — skipping")
        return False

    payload = {}

    if content:
        payload["content"] = content

    if embed:
        # Apply defaults
        embed.setdefault("color", BRAND_COLOR)
        if "footer" not in embed:
            embed["footer"] = {"text": "Short Gravity Terminal"}
        payload["embeds"] = [embed]

    if not payload:
        return False

    body = json.dumps(payload).encode()

    # Retry with backoff (Discord rate limits)
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 204:
                    return True

        except urllib.error.HTTPError as e:
            if e.code == 429:
                try:
                    err_body = json.loads(e.read().decode())
                    retry_after = err_body.get("retry_after", 1)
                except Exception:
                    retry_after = 1
                print(f"[discord] Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            if not silent:
                print(f"[discord] Error {e.code}: {e.read().decode()[:200]}")
            return False

        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if not silent:
                print(f"[discord] Failed after 3 attempts: {e}")
            return False

    return False


def log(message: str, error: bool = False) -> bool:
    """Send a message to #bot-log for worker monitoring."""
    prefix = "ERROR" if error else "INFO"
    return send(Channel.BOT_LOG, content=f"`[{prefix}]` {message}", silent=True)


# --- Formatters for common notification types ---


def notify_sec_filing(form: str, filing_date: str, summary: str, url: str = "") -> bool:
    """Notify #sec-filings of a new SEC filing."""
    embed = {
        "title": f"SEC {form} Filed",
        "description": summary[:2000],
        "fields": [
            {"name": "Form", "value": form, "inline": True},
            {"name": "Date", "value": filing_date, "inline": True},
        ],
    }
    if url:
        embed["url"] = url
    return send(Channel.SEC_FILINGS, embed=embed)


def notify_fcc_filing(title: str, file_number: str, status: str, filed_date: str) -> bool:
    """Notify #fcc-regulatory of FCC activity."""
    embed = {
        "title": f"FCC: {title[:200]}",
        "fields": [
            {"name": "File Number", "value": file_number, "inline": True},
            {"name": "Status", "value": status, "inline": True},
            {"name": "Filed", "value": filed_date, "inline": True},
        ],
    }
    return send(Channel.FCC_REGULATORY, embed=embed)


def notify_patent(patent_number: str, title: str, status: str, source: str = "") -> bool:
    """Notify #patents of a new patent or grant."""
    embed = {
        "title": f"Patent: {patent_number}",
        "description": title[:2000],
        "fields": [
            {"name": "Status", "value": status, "inline": True},
            {"name": "Source", "value": source or "—", "inline": True},
        ],
    }
    return send(Channel.PATENTS, embed=embed)


def notify_press_release(title: str, date: str, url: str = "") -> bool:
    """Notify #press-releases of official announcements."""
    embed = {
        "title": title[:256],
        "fields": [
            {"name": "Date", "value": date, "inline": True},
        ],
    }
    if url:
        embed["url"] = url
    return send(Channel.PRESS_RELEASES, embed=embed)


def notify_launch(mission: str, date: str, status: str) -> bool:
    """Notify #launches of launch events."""
    embed = {
        "title": f"Launch: {mission}",
        "fields": [
            {"name": "Date", "value": date, "inline": True},
            {"name": "Status", "value": status, "inline": True},
        ],
    }
    return send(Channel.LAUNCHES, embed=embed)


def notify_earnings(title: str, date: str, summary: str = "") -> bool:
    """Notify #earnings of new transcript."""
    embed = {
        "title": title[:256],
        "fields": [
            {"name": "Date", "value": date, "inline": True},
        ],
    }
    if summary:
        embed["description"] = summary[:2000]
    return send(Channel.EARNINGS, embed=embed)


def notify_orbital(event: str, details: str) -> bool:
    """Notify #orbital-ops of orbital events."""
    embed = {
        "title": f"Orbital: {event}",
        "description": details[:2000],
    }
    return send(Channel.ORBITAL_OPS, embed=embed)


def notify_signal(signal_type: str, description: str, severity: str = "medium") -> bool:
    """Notify #signals of cross-source anomalies."""
    color_map = {"low": 0x71717A, "medium": 0xFF6B35, "high": 0xFF0000}
    embed = {
        "title": f"Signal: {signal_type}",
        "description": description[:2000],
        "color": color_map.get(severity, BRAND_COLOR),
    }
    return send(Channel.SIGNALS, embed=embed)
