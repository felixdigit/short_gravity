#!/bin/bash
#
# Full FCC Filing Ingestion Pipeline
#
# Runs all FCC workers sequentially to achieve complete filing coverage.
# Expected runtime: 2-4 hours depending on rate limits and PDF sizes.
#
# Usage:
#   cd scripts/data-fetchers
#   export $(grep -v '^#' .env | xargs)
#   ./run_full_fcc_ingestion.sh
#

set -e

echo "============================================================"
echo "FCC Full Ingestion Pipeline"
echo "Started: $(date)"
echo "============================================================"
echo ""

# Check environment
if [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "ERROR: SUPABASE_SERVICE_KEY not set"
    echo "Run: export \$(grep -v '^#' .env | xargs)"
    exit 1
fi

# Step 1: Run content audit (baseline)
echo ""
echo "============================================================"
echo "STEP 1/6: Running content audit (baseline)"
echo "============================================================"
python3 fcc_content_audit.py --quiet

# Step 2: Ingest ECFS filings from critical dockets
echo ""
echo "============================================================"
echo "STEP 2/6: Ingesting ECFS filings - Docket 23-65 (SCS Rulemaking)"
echo "============================================================"
python3 ecfs_worker_v2.py --docket 23-65

echo ""
echo "============================================================"
echo "STEP 3/6: Ingesting ECFS filings - Docket 22-271 (SCS Framework)"
echo "============================================================"
python3 ecfs_worker_v2.py --docket 22-271

# Step 4: Ingest remaining ECFS dockets
echo ""
echo "============================================================"
echo "STEP 4/6: Ingesting ECFS filings - Other dockets (25-201, 25-306)"
echo "============================================================"
python3 ecfs_worker_v2.py --docket 25-201
python3 ecfs_worker_v2.py --docket 25-306

# Step 5: Ingest ELS experimental licenses
echo ""
echo "============================================================"
echo "STEP 5/6: Ingesting ELS experimental licenses"
echo "============================================================"
python3 uls_worker.py --backfill

# Step 6: Re-process short-content ICFS filings
echo ""
echo "============================================================"
echo "STEP 6/6: Re-processing ICFS filings with short content"
echo "============================================================"
python3 fcc_content_audit.py --fix --short --limit 100
python3 icfs_worker_v2.py --backfill

# Final audit
echo ""
echo "============================================================"
echo "FINAL: Running content audit (results)"
echo "============================================================"
python3 fcc_content_audit.py

echo ""
echo "============================================================"
echo "FCC Full Ingestion Pipeline Complete"
echo "Finished: $(date)"
echo "============================================================"
