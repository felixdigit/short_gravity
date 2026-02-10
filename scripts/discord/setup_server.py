"""
Short Gravity — Discord Server Setup Script

Creates channels, roles, and permissions programmatically via Discord bot.
Run ONCE after creating the server and adding the bot.

Prerequisites:
1. Create server manually in Discord
2. Create a bot at https://discord.com/developers/applications
3. Add bot to server with permissions: Manage Channels, Manage Roles, Send Messages
4. Set DISCORD_BOT_TOKEN in .env

Usage:
    export $(grep -v '^#' .env | xargs)
    python3 setup_server.py
"""

import os
import requests
import time

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

BRAND_ORANGE = 0xFF6B35
WHITE = 0xFFFFFF


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


def create_role(name, color=0, permissions="0"):
    """Create a role."""
    print(f"  Creating role: {name}")
    return api("post", f"/guilds/{GUILD_ID}/roles", json={
        "name": name,
        "color": color,
        "permissions": permissions,
        "mentionable": False,
    })


def create_category(name, permission_overwrites=None):
    """Create a channel category."""
    print(f"  Creating category: {name}")
    payload = {"name": name, "type": 4}  # 4 = category
    if permission_overwrites:
        payload["permission_overwrites"] = permission_overwrites
    return api("post", f"/guilds/{GUILD_ID}/channels", json=payload)


def create_text_channel(name, category_id, permission_overwrites=None, topic=""):
    """Create a text channel under a category."""
    print(f"    Creating channel: #{name}")
    payload = {
        "name": name,
        "type": 0,  # 0 = text
        "parent_id": category_id,
    }
    if topic:
        payload["topic"] = topic
    if permission_overwrites:
        payload["permission_overwrites"] = permission_overwrites
    return api("post", f"/guilds/{GUILD_ID}/channels", json=payload)


def main():
    print("Short Gravity Discord — Server Setup\n")

    # Get @everyone role ID (same as guild ID)
    everyone_id = GUILD_ID

    # --- Roles ---
    print("[1/4] Creating roles...")
    # Check for existing roles to avoid duplicates
    existing_roles = api("get", f"/guilds/{GUILD_ID}/roles")
    existing_names = {r["name"]: r for r in existing_roles}

    if "Full Spectrum" in existing_names:
        full_spectrum = existing_names["Full Spectrum"]
        print(f"  Role already exists: Full Spectrum ({full_spectrum['id']})")
    else:
        full_spectrum = create_role("Full Spectrum", color=BRAND_ORANGE)

    if "Ground Control" not in existing_names:
        # No admin perm — assign admin to this role manually in Discord
        create_role("Ground Control", color=WHITE)
        print("  NOTE: Assign Administrator permission to Ground Control manually in Discord")

    fs_id = full_spectrum["id"]

    # Permission helpers
    # Deny VIEW_CHANNEL for @everyone, allow for Full Spectrum
    def patron_only():
        return [
            {"id": everyone_id, "type": 0, "deny": "1024"},      # deny VIEW_CHANNEL
            {"id": fs_id, "type": 0, "allow": "1024"},            # allow VIEW_CHANNEL
        ]

    def read_only_public():
        return [
            {"id": everyone_id, "type": 0, "deny": "2048"},      # deny SEND_MESSAGES
        ]

    def admin_only():
        return [
            {"id": everyone_id, "type": 0, "deny": "1024"},      # deny VIEW_CHANNEL
        ]

    # --- Categories & Channels ---
    print("\n[2/4] Creating public channels...")
    public_cat = create_category("SHORT GRAVITY")
    create_text_channel("welcome", public_cat["id"],
        permission_overwrites=read_only_public(),
        topic="Welcome to Short Gravity — space sector intelligence")
    create_text_channel("announcements", public_cat["id"],
        permission_overwrites=read_only_public(),
        topic="Major updates and milestones")

    print("\n[3/4] Creating Terminal Feed channels (patron-only)...")
    feed_cat = create_category("TERMINAL FEED", permission_overwrites=patron_only())
    create_text_channel("sec-filings", feed_cat["id"],
        topic="SEC filings — 10-K, 10-Q, 8-K, S-1 with AI summaries")
    create_text_channel("fcc-regulatory", feed_cat["id"],
        topic="FCC filings, spectrum decisions, satellite license status")
    create_text_channel("patents", feed_cat["id"],
        topic="Patent grants, new applications, claim analysis")
    create_text_channel("press-releases", feed_cat["id"],
        topic="Official company announcements")
    create_text_channel("launches", feed_cat["id"],
        topic="Launch events, mission updates, constellation deployment")
    create_text_channel("earnings", feed_cat["id"],
        topic="Earnings call transcripts and summaries")
    create_text_channel("orbital-ops", feed_cat["id"],
        topic="TLE updates, conjunction alerts, constellation health")
    create_text_channel("signals", feed_cat["id"],
        topic="Cross-source anomaly alerts and high-signal events")

    print("\n[4/4] Creating community channels...")
    community_cat = create_category("COMMUNITY", permission_overwrites=patron_only())
    create_text_channel("general", community_cat["id"],
        topic="Discussion")
    create_text_channel("research", community_cat["id"],
        topic="Share findings, ask questions, dig into filings")
    create_text_channel("market-talk", community_cat["id"],
        topic="Price action, short interest, positioning")

    # Admin
    meta_cat = create_category("META", permission_overwrites=admin_only())
    create_text_channel("bot-log", meta_cat["id"],
        topic="Worker run status and errors")

    print("\n--- Done. Server structure created. ---")
    print(f"\nFull Spectrum role ID: {fs_id}")
    print("Next: Set up webhooks for each Terminal Feed channel and add URLs to .env")


if __name__ == "__main__":
    main()
