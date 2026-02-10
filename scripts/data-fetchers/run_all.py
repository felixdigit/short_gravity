#!/usr/bin/env python3
"""
Master Worker Script — Compounding Data Schedule

Runs data fetchers organized by cadence. Each run picks the appropriate
workers based on the --cadence flag.

Cadences:
  frequent  — every 15 min: SEC filings, TLE orbital data
  hourly    — every 4 hours: news, press releases
  daily     — once per day: FCC metadata + attachments, SEC exhibits, patents,
              earnings transcripts, cash position
  weekly    — once per week: short interest, FCC ELS scan, patent enrichment

Usage:
    python3 run_all.py                    # Run all workers (full cycle)
    python3 run_all.py --cadence frequent # Only frequent workers
    python3 run_all.py --cadence daily    # Only daily workers
    python3 run_all.py --dry-run          # Preview what would run
"""

from __future__ import annotations
import argparse
import subprocess
import sys
import os
from datetime import datetime

WORKERS_DIR = os.path.dirname(os.path.abspath(__file__))

# Worker definitions: (name, script, args, timeout_seconds)
FREQUENT_WORKERS = [
    ("SEC Filing Worker", "filing_worker.py", [], 300),
    ("TLE Worker", "tle_worker.py", [], 300),
]

HOURLY_WORKERS = [
    ("News Worker", "news_worker.py", [], 120),
    ("Press Release Worker", "press_release_worker.py", [], 120),
]

DAILY_WORKERS = [
    ("SEC Exhibit Backfill", "exhibit_backfill.py", ["--limit", "50"], 600),
    ("FCC ICFS Metadata", "icfs_servicenow_worker.py", [], 600),
    ("FCC ICFS Attachments", "fcc_attachment_worker.py", ["--icfs-incremental"], 600),
    ("FCC ECFS Docket Crawler", "ecfs_worker.py", ["--no-pdf"], 600),
    ("Cash Position Worker", "cash_position_worker.py", [], 120),
    ("Patent Discovery", "patent_worker_v2.py", [], 600),
    ("Transcript Worker", "transcript_worker.py", [], 600),
]

WEEKLY_WORKERS = [
    ("Short Interest Worker", "short_interest_worker.py", [], 60),
    ("FCC ELS Scanner", "fcc_attachment_worker.py", ["--els-scan"], 600),
    ("Patent Enricher", "patent_enricher.py", ["--missing-only"], 600),
]


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def run_worker(name: str, script: str, args: list, timeout: int) -> bool:
    """Run a single worker script."""
    script_path = os.path.join(WORKERS_DIR, script)
    if not os.path.exists(script_path):
        log(f"  SKIP: {script} not found")
        return False

    log(f"--- {name} ---")

    try:
        env = os.environ.copy()
        # Load .env if not already set
        if not env.get("SUPABASE_SERVICE_KEY"):
            env_path = os.path.join(WORKERS_DIR, ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip()

        result = subprocess.run(
            [sys.executable, script_path] + args,
            cwd=WORKERS_DIR,
            env=env,
            capture_output=False,
            timeout=timeout,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT: {name} exceeded {timeout}s")
        return False
    except Exception as e:
        log(f"  ERROR: {name}: {e}")
        return False


def run_cadence(name: str, workers: list, dry_run: bool = False) -> list:
    """Run all workers for a given cadence."""
    log(f"\n{'=' * 60}")
    log(f"CADENCE: {name.upper()} ({len(workers)} workers)")
    log(f"{'=' * 60}")

    results = []
    for worker_name, script, args, timeout in workers:
        if dry_run:
            log(f"  [DRY RUN] {worker_name} ({script})")
            results.append((worker_name, True))
            continue

        success = run_worker(worker_name, script, args, timeout)
        results.append((worker_name, success))
        log("")

    return results


def main():
    parser = argparse.ArgumentParser(description="Short Gravity Data Scheduler")
    parser.add_argument("--cadence", choices=["frequent", "hourly", "daily", "weekly", "all"],
                        default="all", help="Which cadence to run")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")
    args = parser.parse_args()

    log("=" * 60)
    log("SHORT GRAVITY COMPOUNDING DATA SCHEDULE")
    log(f"Cadence: {args.cadence}")
    log("=" * 60)

    all_results = []

    cadences = {
        "frequent": ("Frequent (15 min)", FREQUENT_WORKERS),
        "hourly": ("Hourly (4 hr)", HOURLY_WORKERS),
        "daily": ("Daily", DAILY_WORKERS),
        "weekly": ("Weekly", WEEKLY_WORKERS),
    }

    if args.cadence == "all":
        for key, (name, workers) in cadences.items():
            all_results.extend(run_cadence(name, workers, args.dry_run))
    else:
        name, workers = cadences[args.cadence]
        all_results.extend(run_cadence(name, workers, args.dry_run))

    # Summary
    log(f"\n{'=' * 60}")
    log("SUMMARY")
    log(f"{'=' * 60}")
    for name, success in all_results:
        status = "OK" if success else "FAIL"
        log(f"  [{status:4s}] {name}")
    log(f"\nTotal: {sum(1 for _, s in all_results if s)}/{len(all_results)} succeeded")
    log("Done.")


if __name__ == "__main__":
    main()
