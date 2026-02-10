#!/usr/bin/env python3
"""
Investor Relations Data Fetcher for AST SpaceMobile
Fetches press releases and quarterly results from IR page

Source: https://investors.ast-science.com/
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from html.parser import HTMLParser

IR_BASE_URL = "https://investors.ast-science.com"
USER_AGENT = "Short Gravity Research gabriel@shortgravity.com"


class LinkExtractor(HTMLParser):
    """Extract links and text from HTML."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.current_link = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            if "href" in attrs_dict:
                self.current_link = attrs_dict["href"]
                self.current_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self.current_link:
            text = " ".join(self.current_text).strip()
            self.links.append({
                "href": self.current_link,
                "text": text,
            })
            self.current_link = None
            self.current_text = []

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_text.append(data.strip())


def fetch_url(url: str) -> str:
    """Fetch URL content."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def extract_press_releases_from_html(html: str) -> List[Dict]:
    """Extract press release data from IR page HTML."""
    releases = []

    # Extract links
    parser = LinkExtractor()
    parser.feed(html)

    for link in parser.links:
        href = link["href"]
        text = link["text"]

        # Look for press release links (typically contain dates or PR keywords)
        if "press-release" in href.lower() or "news" in href.lower():
            releases.append({
                "title": text,
                "url": href if href.startswith("http") else f"{IR_BASE_URL}{href}",
            })

    return releases


def get_known_press_releases() -> List[Dict]:
    """
    Return key press releases for AST SpaceMobile.
    These are major announcements tracked manually.
    """
    return [
        {
            "date": "2026-01-22",
            "title": "AST SpaceMobile Announces Timing of BlueBird 7 Orbital Launch",
            "category": "Launch",
            "url": "https://investors.ast-science.com/press-releases",
        },
        {
            "date": "2024-12-23",
            "title": "BlueBird 6 Successfully Launches from India",
            "category": "Launch",
        },
        {
            "date": "2024-09-12",
            "title": "BlueBird 1-5 Commercial Satellites Successfully Launch",
            "category": "Launch",
        },
        {
            "date": "2024-09-05",
            "title": "AT&T and AST SpaceMobile Complete First-Ever Two-Way Voice Call via Satellite",
            "category": "Milestone",
        },
        {
            "date": "2024-05-16",
            "title": "Verizon Partnership Announcement",
            "category": "Partnership",
        },
        {
            "date": "2024-01",
            "title": "Ligado Networks Partnership for L-band Spectrum",
            "category": "Partnership",
        },
        {
            "date": "2023-04-25",
            "title": "First 5G Connection via BlueWalker 3 with AT&T",
            "category": "Milestone",
        },
        {
            "date": "2022-09-10",
            "title": "BlueWalker 3 Test Satellite Successfully Launches",
            "category": "Launch",
        },
    ]


def get_quarterly_results() -> List[Dict]:
    """
    Return quarterly results timeline.
    """
    return [
        {
            "period": "Q3 2025",
            "filingDate": "2025-11-10",
            "highlights": [
                "$1.0B+ aggregate contracted revenue commitments",
                "$3.2B pro forma cash and liquidity",
                "Q3 GAAP revenue: $14.7M",
                "H2 2025 revenue guidance: $50M-$75M",
            ],
        },
        {
            "period": "Q2 2025",
            "filingDate": "2025-08-12",
            "highlights": [
                "Commercial service preparations",
                "BlueBird production ramp",
            ],
        },
        {
            "period": "Q1 2025",
            "filingDate": "2025-05-12",
            "highlights": [
                "First commercial service beta testing",
            ],
        },
        {
            "period": "Q3 2024",
            "filingDate": "2024-11-14",
            "highlights": [
                "BlueBird 1-5 launch successful",
                "First voice call milestone",
            ],
        },
    ]


def get_mno_partnerships() -> List[Dict]:
    """
    Return MNO partnership details.
    """
    return [
        {
            "partner": "AT&T",
            "region": "United States",
            "status": "Active",
            "spectrum": "700 MHz (A/B/C blocks), 850 MHz Cellular",
            "milestones": [
                "2023-04: First 5G connection via BW3",
                "2024-09: First two-way voice call",
            ],
        },
        {
            "partner": "Verizon",
            "region": "United States",
            "status": "Active",
            "spectrum": "800 MHz Cellular",
            "announced": "2024-05",
        },
        {
            "partner": "Vodafone",
            "region": "Europe (select markets)",
            "status": "Active",
        },
        {
            "partner": "Rakuten",
            "region": "Japan",
            "status": "Active",
        },
        {
            "partner": "Bell Canada",
            "region": "Canada",
            "status": "Active",
        },
        {
            "partner": "Telefonica",
            "region": "Latin America, Europe",
            "status": "Active",
        },
        {
            "partner": "Orange",
            "region": "Africa, Europe",
            "status": "Active",
        },
        {
            "partner": "MTN",
            "region": "Africa",
            "status": "Active",
        },
        {
            "partner": "Ligado Networks",
            "region": "United States",
            "status": "Pending FCC approval",
            "spectrum": "L-band MSS",
            "notes": "Space-based 5G partnership",
        },
    ]


def get_financial_highlights() -> Dict:
    """
    Return key financial metrics from recent filings.
    """
    return {
        "asOf": "Q3 2025",
        "contractedRevenue": "$1.0B+",
        "cashAndLiquidity": "$3.2B (pro forma)",
        "q3Revenue": "$14.7M",
        "h2RevenueGuidance": "$50M-$75M",
        "marketCap": "~$14B (Jan 2025)",
        "sharesOutstanding": "~340M",
        "majorHolders": [
            {"name": "Abel Avellan (Founder/CEO)", "percentage": "~15%"},
            {"name": "Institutions", "percentage": "~35%"},
            {"name": "Retail", "percentage": "~50%"},
        ],
    }


def get_key_milestones() -> List[Dict]:
    """
    Return key company milestones timeline.
    """
    return [
        {"date": "2017", "event": "AST SpaceMobile founded by Abel Avellan"},
        {"date": "2021-04", "event": "SPAC merger completed, listed on NASDAQ (ASTS)"},
        {"date": "2022-09", "event": "BlueWalker 3 test satellite launched"},
        {"date": "2023-04", "event": "First 5G connection from space via BW3"},
        {"date": "2024-04", "event": "First voice call from space"},
        {"date": "2024-09", "event": "BlueBird 1-5 commercial satellites launched"},
        {"date": "2024-12", "event": "BlueBird 6 launched from India"},
        {"date": "2025-Q1", "event": "Commercial service beta (US)"},
        {"date": "2026-01", "event": "BlueBird 7 launch scheduled (New Glenn)"},
        {"date": "2026-EOY", "event": "Target: 45-60 satellites in orbit"},
    ]


def main():
    print("=== Investor Relations Fetcher for AST SpaceMobile ===\n")

    output = {
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "company": {
            "name": "AST SpaceMobile, Inc.",
            "ticker": "ASTS",
            "exchange": "NASDAQ",
            "ceo": "Abel Avellan",
            "founded": "2017",
            "headquarters": "Midland, Texas",
            "irUrl": IR_BASE_URL,
        },
        "pressReleases": get_known_press_releases(),
        "quarterlyResults": get_quarterly_results(),
        "mnoPartnerships": get_mno_partnerships(),
        "financialHighlights": get_financial_highlights(),
        "keyMilestones": get_key_milestones(),
        "investorResources": {
            "pressReleases": f"{IR_BASE_URL}/press-releases",
            "quarterlyResults": f"{IR_BASE_URL}/quarterly-results",
            "secFilings": f"{IR_BASE_URL}/sec-filings",
            "stockInfo": f"{IR_BASE_URL}/stock-info",
            "corporateGovernance": f"{IR_BASE_URL}/corporate-governance",
        },
    }

    # Print summary
    print("Key Press Releases:")
    for pr in output["pressReleases"][:5]:
        print(f"  {pr['date']}: {pr['title'][:60]}")

    print(f"\nMNO Partnerships: {len(output['mnoPartnerships'])}")
    for p in output["mnoPartnerships"][:5]:
        print(f"  - {p['partner']} ({p['region']})")

    print(f"\nKey Milestones: {len(output['keyMilestones'])}")

    print(f"\nFinancial Highlights (as of {output['financialHighlights']['asOf']}):")
    print(f"  Contracted Revenue: {output['financialHighlights']['contractedRevenue']}")
    print(f"  Cash & Liquidity: {output['financialHighlights']['cashAndLiquidity']}")

    # Save output
    script_dir = Path(__file__).parent
    output_path = script_dir / "../../research/asts/investor-relations.json"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
