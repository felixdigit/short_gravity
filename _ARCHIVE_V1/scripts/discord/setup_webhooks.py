"""
Short Gravity — Discord Webhook Setup

Creates webhooks for all notification channels and outputs env vars.
Run ONCE after setup_server.py has created the channels.

Usage:
    export $(grep -v '^#' .env | xargs)
    python3 setup_webhooks.py
"""

import os
import time
import requests

BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

if not BOT_TOKEN or not GUILD_ID:
    print("Set DISCORD_BOT_TOKEN and DISCORD_GUILD_ID in .env")
    exit(1)

HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json",
}

BASE = "https://discord.com/api/v10"

# Channel name → env var mapping
CHANNEL_WEBHOOK_MAP = {
    "sec-filings": "DISCORD_WEBHOOK_SEC",
    "fcc-regulatory": "DISCORD_WEBHOOK_FCC",
    "patents": "DISCORD_WEBHOOK_PATENTS",
    "press-releases": "DISCORD_WEBHOOK_PRESS",
    "launches": "DISCORD_WEBHOOK_LAUNCHES",
    "earnings": "DISCORD_WEBHOOK_EARNINGS",
    "orbital-ops": "DISCORD_WEBHOOK_ORBITAL",
    "signals": "DISCORD_WEBHOOK_SIGNALS",
    "bot-log": "DISCORD_WEBHOOK_BOT_LOG",
}


def api(method, path, json=None):
    """Make a Discord API call with rate limit handling."""
    for attempt in range(3):
        resp = getattr(requests, method)(f"{BASE}{path}", headers=HEADERS, json=json, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 1)
            print(f"  Rate limited, waiting {retry_after}s")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()
    raise Exception("Rate limited 3 times")


def main():
    print("Short Gravity Discord — Webhook Setup\n")

    # Get all channels
    channels = api("get", f"/guilds/{GUILD_ID}/channels")
    channel_map = {ch["name"]: ch["id"] for ch in channels}

    webhook_env_lines = []

    for channel_name, env_var in CHANNEL_WEBHOOK_MAP.items():
        channel_id = channel_map.get(channel_name)
        if not channel_id:
            print(f"  SKIP: #{channel_name} not found")
            continue

        # Check for existing webhooks to avoid duplicates
        existing = api("get", f"/channels/{channel_id}/webhooks")
        sg_hooks = [w for w in existing if w.get("name") == "Short Gravity"]
        if sg_hooks:
            url = sg_hooks[0]["url"]
            print(f"  EXISTS: #{channel_name} → {env_var}")
        else:
            webhook = api("post", f"/channels/{channel_id}/webhooks", json={
                "name": "Short Gravity",
            })
            url = webhook["url"]
            print(f"  CREATED: #{channel_name} → {env_var}")
            time.sleep(0.5)  # Be gentle with rate limits

        webhook_env_lines.append(f"{env_var}={url}")

    print("\n--- Webhook URLs ---\n")
    for line in webhook_env_lines:
        print(line)

    # Write to a temp file for easy copy
    out_path = os.path.join(os.path.dirname(__file__), "webhook_urls.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(webhook_env_lines) + "\n")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
