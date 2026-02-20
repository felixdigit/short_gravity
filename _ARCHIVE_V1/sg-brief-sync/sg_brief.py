#!/usr/bin/env python3
"""
Short Gravity Brief — Google Docs Sync Tool

Manages a living Google Doc that bridges the Short Gravity and LinkedIn
Claude Projects. Supports create, update, read, and append operations
via the Google Docs API.

Usage:
    python sg_brief.py create                      # Create the doc for the first time
    python sg_brief.py update --file brief.md      # Replace doc content from a file
    python sg_brief.py update --text "..."         # Replace doc content from text
    python sg_brief.py append --file update.md     # Append content to the doc
    python sg_brief.py append --text "..."         # Append text to the doc
    python sg_brief.py read                        # Print current doc content
    python sg_brief.py link                        # Print the doc URL
    python sg_brief.py auth                        # Run OAuth flow only (setup)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete token.json and re-authenticate
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

DOC_TITLE = "Short Gravity — Latest Brief"


# ─── Auth ─────────────────────────────────────────────────────────────────────

def get_credentials():
    """Handle OAuth2 authentication. Opens browser on first run."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"ERROR: {CREDENTIALS_FILE} not found.")
                print()
                print("Setup steps:")
                print("  1. Go to https://console.cloud.google.com")
                print("  2. Create a project (or select existing)")
                print("  3. Enable 'Google Docs API' and 'Google Drive API'")
                print("  4. Go to Credentials → Create Credentials → OAuth Client ID")
                print("  5. Application type: Desktop app")
                print("  6. Download the JSON and save it as:")
                print(f"     {CREDENTIALS_FILE}")
                print()
                print("Then run: python sg_brief.py auth")
                sys.exit(1)

            print("Opening browser for Google authentication...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("Authentication successful. Token saved.")

    return creds


def get_services(creds):
    """Build Google Docs and Drive service objects."""
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return docs, drive


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config():
    """Load config (stores doc ID)."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save config."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_doc_id():
    """Get the stored document ID, or exit with instructions."""
    config = load_config()
    doc_id = config.get("doc_id")
    if not doc_id:
        print("ERROR: No document found. Run 'python sg_brief.py create' first.")
        sys.exit(1)
    return doc_id


# ─── Helpers ──────────────────────────────────────────────────────────────────

def read_input(args):
    """Read content from --file or --text argument."""
    if hasattr(args, "file") and args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(1)
        return path.read_text(encoding="utf-8")
    elif hasattr(args, "text") and args.text:
        return args.text
    else:
        # Read from stdin if piped
        if not sys.stdin.isatty():
            return sys.stdin.read()
        print("ERROR: Provide content via --file, --text, or stdin pipe.")
        sys.exit(1)


def clear_doc(docs_service, doc_id):
    """Remove all content from a Google Doc (except the trailing newline)."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])

    # Find the end index (last structural element before the final newline)
    end_index = 1
    for element in content:
        if "endIndex" in element:
            end_index = element["endIndex"]

    if end_index > 2:
        requests = [
            {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}}
        ]
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()


def insert_text(docs_service, doc_id, text, index=1):
    """Insert text at a given index in the doc."""
    requests = [{"insertText": {"location": {"index": index}, "text": text}}]
    docs_service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()


def add_timestamp_footer(text):
    """Append a sync timestamp to the content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    footer = f"\n\n---\nLast synced: {now}\n"
    return text.rstrip() + footer


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_auth(args):
    """Run OAuth flow only."""
    get_credentials()
    print("Ready to go.")


def cmd_create(args):
    """Create the Google Doc for the first time."""
    config = load_config()
    if config.get("doc_id"):
        print(f"Document already exists: https://docs.google.com/document/d/{config['doc_id']}/edit")
        print("Use 'update' to replace its content, or delete config.json to start fresh.")
        return

    creds = get_credentials()
    docs, drive = get_services(creds)

    # Create the document
    doc = docs.documents().create(body={"title": DOC_TITLE}).execute()
    doc_id = doc["documentId"]

    # Save the doc ID
    config["doc_id"] = doc_id
    config["created_at"] = datetime.now(timezone.utc).isoformat()
    save_config(config)

    # Insert placeholder content
    placeholder = (
        f"{DOC_TITLE}\n\n"
        "This document is auto-managed by the SG Brief sync tool.\n"
        "Run 'python sg_brief.py update --file brief.md' to populate it.\n"
    )
    insert_text(docs, doc_id, add_timestamp_footer(placeholder))

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"Document created: {url}")
    print(f"Doc ID saved to {CONFIG_FILE}")


def cmd_update(args):
    """Replace the entire doc content."""
    doc_id = get_doc_id()
    content = read_input(args)

    creds = get_credentials()
    docs, _ = get_services(creds)

    clear_doc(docs, doc_id)
    insert_text(docs, doc_id, add_timestamp_footer(content))

    print(f"Document updated: https://docs.google.com/document/d/{doc_id}/edit")


def cmd_append(args):
    """Append content to the end of the doc."""
    doc_id = get_doc_id()
    content = read_input(args)

    creds = get_credentials()
    docs, _ = get_services(creds)

    # Get current doc length
    doc = docs.documents().get(documentId=doc_id).execute()
    body_content = doc.get("body", {}).get("content", [])
    end_index = 1
    for element in body_content:
        if "endIndex" in element:
            end_index = element["endIndex"]

    # Insert before the final newline
    insert_index = max(end_index - 1, 1)
    insert_text(docs, doc_id, "\n\n" + content.strip(), index=insert_index)

    print(f"Content appended: https://docs.google.com/document/d/{doc_id}/edit")


def cmd_read(args):
    """Print the current doc content."""
    doc_id = get_doc_id()

    creds = get_credentials()
    docs, _ = get_services(creds)

    doc = docs.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])

    text_parts = []
    for element in content:
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    text_parts.append(run["textRun"]["content"])

    print("".join(text_parts))


def cmd_link(args):
    """Print the document URL."""
    doc_id = get_doc_id()
    print(f"https://docs.google.com/document/d/{doc_id}/edit")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Short Gravity Brief — Google Docs Sync Tool"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # auth
    subparsers.add_parser("auth", help="Run OAuth flow (setup)")

    # create
    subparsers.add_parser("create", help="Create the Google Doc")

    # update
    p_update = subparsers.add_parser("update", help="Replace doc content")
    p_update.add_argument("--file", "-f", help="Read content from file")
    p_update.add_argument("--text", "-t", help="Content as string")

    # append
    p_append = subparsers.add_parser("append", help="Append to doc")
    p_append.add_argument("--file", "-f", help="Read content from file")
    p_append.add_argument("--text", "-t", help="Content as string")

    # read
    subparsers.add_parser("read", help="Print current doc content")

    # link
    subparsers.add_parser("link", help="Print the doc URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "auth": cmd_auth,
        "create": cmd_create,
        "update": cmd_update,
        "append": cmd_append,
        "read": cmd_read,
        "link": cmd_link,
    }

    try:
        commands[args.command](args)
    except HttpError as e:
        print(f"Google API error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
