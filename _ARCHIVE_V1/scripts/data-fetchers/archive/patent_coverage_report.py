#!/usr/bin/env python3
"""
Patent Data Coverage Report

Analyzes patent data completeness and consistency across the database.
Generates a markdown report showing coverage by jurisdiction and identifying gaps.

Usage:
    python3 patent_coverage_report.py
    python3 patent_coverage_report.py --output report.md

Requirements: None (uses stdlib only)
"""

import argparse
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method, endpoint, data=None):
    """Make Supabase REST API request."""
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
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise Exception(f"HTTP {e.code}: {error_body[:200]}")


def get_jurisdiction(patent_number):
    """Extract jurisdiction from patent number."""
    if not patent_number:
        return "UNKNOWN"
    pn = patent_number.upper()
    for prefix in ["US", "EP", "WO", "JP", "KR", "AU", "CA", "CN", "DK", "ES", "GB", "DE", "FR"]:
        if pn.startswith(prefix):
            return prefix
    return "OTHER"


def generate_report():
    """Generate comprehensive patent coverage report."""
    log("Fetching patent data...")

    # Get all patents
    patents = supabase_request(
        "GET",
        "patents?select=patent_number,title,abstract,figure_urls,claims_count,source_url,status&limit=1000"
    )
    log(f"Found {len(patents)} patents")

    # Get all claims (paginate to get full count)
    all_claims = []
    offset = 0
    batch_size = 1000
    while True:
        batch = supabase_request("GET", f"patent_claims?select=patent_number,claim_number,claim_type&limit={batch_size}&offset={offset}")
        if not batch:
            break
        all_claims.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    claims = all_claims
    log(f"Found {len(claims)} claims")

    # Build claims lookup
    claims_by_patent = defaultdict(list)
    for c in claims:
        claims_by_patent[c["patent_number"]].append(c)

    # Analyze by jurisdiction
    by_jurisdiction = defaultdict(lambda: {
        "total": 0,
        "has_title": 0,
        "has_abstract": 0,
        "has_figures": 0,
        "has_claims": 0,
        "has_source_url": 0,
        "missing_title": [],
        "missing_abstract": [],
        "missing_figures": [],
        "missing_claims": [],
        "claims_mismatch": [],
    })

    issues = {
        "duplicates": [],
        "malformed_numbers": [],
        "empty_titles": [],
        "claims_count_mismatch": [],
    }

    seen_numbers = set()

    for p in patents:
        pn = p.get("patent_number", "")
        jur = get_jurisdiction(pn)
        j = by_jurisdiction[jur]

        j["total"] += 1

        # Check for duplicates
        if pn in seen_numbers:
            issues["duplicates"].append(pn)
        seen_numbers.add(pn)

        # Check patent number format
        if not pn or len(pn) < 5:
            issues["malformed_numbers"].append(pn or "(empty)")

        # Title check
        has_title = p.get("title") and p["title"] != "[no title]" and len(p["title"]) > 3
        if has_title:
            j["has_title"] += 1
        else:
            j["missing_title"].append(pn)
            if p.get("title") == "[no title]":
                issues["empty_titles"].append(pn)

        # Abstract check
        has_abstract = p.get("abstract") and len(p.get("abstract", "")) > 20
        if has_abstract:
            j["has_abstract"] += 1
        else:
            j["missing_abstract"].append(pn)

        # Figures check
        has_figures = p.get("figure_urls") and len(p.get("figure_urls", [])) > 0
        if has_figures:
            j["has_figures"] += 1
        else:
            j["missing_figures"].append(pn)

        # Claims check
        actual_claims = len(claims_by_patent.get(pn, []))
        if actual_claims > 0:
            j["has_claims"] += 1
        else:
            j["missing_claims"].append(pn)

        # Claims count mismatch
        expected = p.get("claims_count") or 0
        if expected > 0 and actual_claims > 0 and abs(expected - actual_claims) > 2:
            issues["claims_count_mismatch"].append({
                "patent": pn,
                "expected": expected,
                "actual": actual_claims,
            })
            j["claims_mismatch"].append(pn)

        # Source URL check
        if p.get("source_url"):
            j["has_source_url"] += 1

    # Generate markdown report
    report = []
    report.append("# Patent Data Coverage Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Total Patents:** {len(patents)}")
    report.append(f"**Total Claims:** {len(claims)}")

    # Summary table
    report.append("\n## Coverage Summary by Jurisdiction\n")
    report.append("| Jurisdiction | Total | Title | Abstract | Figures | Claims | PDF URL |")
    report.append("|--------------|-------|-------|----------|---------|--------|---------|")

    totals = {"total": 0, "title": 0, "abstract": 0, "figures": 0, "claims": 0, "pdf": 0}

    for jur in sorted(by_jurisdiction.keys()):
        j = by_jurisdiction[jur]
        totals["total"] += j["total"]
        totals["title"] += j["has_title"]
        totals["abstract"] += j["has_abstract"]
        totals["figures"] += j["has_figures"]
        totals["claims"] += j["has_claims"]
        totals["pdf"] += j["has_source_url"]

        report.append(
            f"| {jur} | {j['total']} | {j['has_title']} | {j['has_abstract']} | "
            f"{j['has_figures']} | {j['has_claims']} | {j['has_source_url']} |"
        )

    report.append(
        f"| **TOTAL** | **{totals['total']}** | **{totals['title']}** | **{totals['abstract']}** | "
        f"**{totals['figures']}** | **{totals['claims']}** | **{totals['pdf']}** |"
    )

    # Coverage percentages
    report.append("\n### Coverage Percentages\n")
    if totals["total"] > 0:
        report.append(f"- **Titles:** {totals['title']/totals['total']*100:.1f}%")
        report.append(f"- **Abstracts:** {totals['abstract']/totals['total']*100:.1f}%")
        report.append(f"- **Figures:** {totals['figures']/totals['total']*100:.1f}%")
        report.append(f"- **Claims:** {totals['claims']/totals['total']*100:.1f}%")
        report.append(f"- **PDF URLs:** {totals['pdf']/totals['total']*100:.1f}%")

    # Missing data details
    report.append("\n## Missing Data by Jurisdiction\n")

    for jur in sorted(by_jurisdiction.keys()):
        j = by_jurisdiction[jur]
        missing_any = j["missing_title"] or j["missing_abstract"] or j["missing_figures"] or j["missing_claims"]

        if missing_any:
            report.append(f"\n### {jur} ({j['total']} patents)\n")

            if j["missing_title"]:
                report.append(f"**Missing titles ({len(j['missing_title'])}):** {', '.join(j['missing_title'][:10])}")
                if len(j["missing_title"]) > 10:
                    report.append(f" ...and {len(j['missing_title']) - 10} more")

            if j["missing_claims"]:
                report.append(f"\n**Missing claims ({len(j['missing_claims'])}):** {', '.join(j['missing_claims'][:10])}")
                if len(j["missing_claims"]) > 10:
                    report.append(f" ...and {len(j['missing_claims']) - 10} more")

    # Claims analysis
    report.append("\n## Claims Analysis\n")

    # Count claims by type
    independent_claims = sum(1 for c in claims if c.get("claim_type") == "independent")
    dependent_claims = sum(1 for c in claims if c.get("claim_type") == "dependent")

    report.append(f"- **Total claims in DB:** {len(claims)}")
    report.append(f"- **Independent claims:** {independent_claims}")
    report.append(f"- **Dependent claims:** {dependent_claims}")
    report.append(f"- **Patents with claims:** {totals['claims']}")
    report.append(f"- **Patents missing claims:** {totals['total'] - totals['claims']}")

    if issues["claims_count_mismatch"]:
        report.append(f"\n### Claims Count Mismatches ({len(issues['claims_count_mismatch'])})\n")
        report.append("| Patent | Expected | Actual | Diff |")
        report.append("|--------|----------|--------|------|")
        for m in issues["claims_count_mismatch"][:20]:
            diff = m["actual"] - m["expected"]
            report.append(f"| {m['patent']} | {m['expected']} | {m['actual']} | {diff:+d} |")

    # Data quality issues
    report.append("\n## Data Quality Issues\n")

    if issues["duplicates"]:
        report.append(f"### Duplicate Patent Numbers ({len(issues['duplicates'])})")
        report.append(f"{', '.join(issues['duplicates'])}\n")
    else:
        report.append("- No duplicate patent numbers found")

    if issues["malformed_numbers"]:
        report.append(f"\n### Malformed Patent Numbers ({len(issues['malformed_numbers'])})")
        report.append(f"{', '.join(issues['malformed_numbers'])}\n")
    else:
        report.append("- No malformed patent numbers found")

    if issues["empty_titles"]:
        report.append(f"\n### Patents with '[no title]' ({len(issues['empty_titles'])})")
        report.append(f"{', '.join(issues['empty_titles'][:20])}")
        if len(issues["empty_titles"]) > 20:
            report.append(f" ...and {len(issues['empty_titles']) - 20} more")

    # Recommendations
    report.append("\n## Recommendations\n")

    recommendations = []

    # Check for significant gaps
    missing_claims_pct = (totals["total"] - totals["claims"]) / totals["total"] * 100 if totals["total"] > 0 else 0
    missing_abstracts_pct = (totals["total"] - totals["abstract"]) / totals["total"] * 100 if totals["total"] > 0 else 0
    missing_figures_pct = (totals["total"] - totals["figures"]) / totals["total"] * 100 if totals["total"] > 0 else 0

    if missing_claims_pct > 50:
        recommendations.append(f"1. **Claims coverage is low ({100-missing_claims_pct:.0f}%)**. Re-run `patent_enricher.py --missing-only` to scrape claims from Google Patents.")

    if missing_abstracts_pct > 70:
        recommendations.append(f"2. **Abstracts coverage is low ({100-missing_abstracts_pct:.0f}%)**. Note: Many Google Patents pages don't have English abstracts for non-US patents.")

    if missing_figures_pct > 50:
        recommendations.append(f"3. **Figures coverage is low ({100-missing_figures_pct:.0f}%)**. Re-run enricher to capture figure URLs from Google Patents.")

    # Check US patents specifically
    us_data = by_jurisdiction.get("US", {})
    if us_data.get("total", 0) > 0:
        us_missing_claims = len(us_data.get("missing_claims", []))
        if us_missing_claims > us_data["total"] * 0.5:
            recommendations.append(f"4. **US patents missing claims ({us_missing_claims}/{us_data['total']})**. US B1/B2 patents often return 404 on Google Patents. Consider using PatentsView API or BigQuery for US claims.")

    if not recommendations:
        recommendations.append("Data coverage looks good! No major gaps identified.")

    for rec in recommendations:
        report.append(rec)

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Generate patent data coverage report")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    log("=" * 60)
    log("PATENT DATA COVERAGE REPORT")
    log("=" * 60)

    report = generate_report()

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        log(f"Report written to: {args.output}")
    else:
        print("\n" + report)

    log("=" * 60)
    log("DONE")
    log("=" * 60)


if __name__ == "__main__":
    main()
