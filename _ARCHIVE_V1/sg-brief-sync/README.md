# SG Brief Sync

CLI tool that manages the **Short Gravity — Latest Brief** Google Doc via the Google Docs API. This doc bridges the Short Gravity and LinkedIn Claude Projects.

## First-Time Setup (one time only)

```bash
cd sg-brief-sync
pip install -r requirements.txt
python sg_brief.py auth
```

The `auth` command opens your browser — sign in, allow access, done. The Google Doc already exists (config.json has the ID).

## Usage

```bash
# Replace the entire doc with content from a file
python sg_brief.py update --file brief.md

# Replace with inline text
python sg_brief.py update --text "New content here"

# Replace via stdin pipe
echo "Content" | python sg_brief.py update

# Append to the doc
python sg_brief.py append --file update.md

# Read current content
python sg_brief.py read

# Get the doc URL
python sg_brief.py link
```

## Claude Code Workflow

When working in Claude Code on Short Gravity and something meaningful changes:

1. Save the updated brief as `brief.md`
2. Run: `python sg_brief.py update --file brief.md`

Or pipe directly: `echo "updated content" | python sg_brief.py update`

The LinkedIn Claude Project reads this doc via Google Drive search — no setup needed on that side.

## How It Fits Together

```
Short Gravity work (Claude Code or Claude Project)
        │
        │  generate/update brief
        ▼
   sg_brief.py update --file brief.md
        │
        │  writes via Google Docs API
        ▼
   Google Doc: "Short Gravity — Latest Brief"
        │
        │  Claude reads natively via Drive search
        ▼
   LinkedIn Claude Project
   "Pull the SG brief from Google Drive"
```

## Files

| File | Purpose | Git tracked? |
|------|---------|-------------|
| `sg_brief.py` | Main CLI tool | ✅ |
| `requirements.txt` | Python dependencies | ✅ |
| `credentials.json` | Google OAuth client secret | ❌ |
| `token.json` | Your auth token (created after `auth`) | ❌ |
| `config.json` | Stores the Google Doc ID | ❌ |
