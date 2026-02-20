/**
 * Mock Signal Generator — Unseeded database fallback.
 *
 * Produces realistic AST SpaceMobile signals for frontend telemetry
 * when the database has no live data. All values derived from actual
 * ASTS orbital parameters and regulatory filings.
 */

import type { Signal } from "../schemas";
import {
  anomalyTypeEnum,
  severityEnum,
} from "@shortgravity/database/schema";

// Compile-time proof that our literals are valid enum members.
const _ORB_DEV: (typeof anomalyTypeEnum.enumValues)[number] = "ORB-DEV";
const _REG_UNU: (typeof anomalyTypeEnum.enumValues)[number] = "REG-UNU";
const _ORB_MAN: (typeof anomalyTypeEnum.enumValues)[number] = "ORB-MAN";
const _CRITICAL: (typeof severityEnum.enumValues)[number] = "critical";
const _HIGH: (typeof severityEnum.enumValues)[number] = "high";
const _LOW: (typeof severityEnum.enumValues)[number] = "low";

// Deterministic UUIDs for reproducible mock state.
const ENTITY_ID_BW3 = "a1b2c3d4-0001-4000-8000-000000000001";
const ENTITY_ID_ASTS = "a1b2c3d4-0002-4000-8000-000000000002";
const ENTITY_ID_BW7 = "a1b2c3d4-0003-4000-8000-000000000003";

/**
 * Generate an array of realistic mock signals for AST SpaceMobile.
 *
 * Returns 3 signals covering the critical telemetry archetypes:
 *   1. CRITICAL ORB-DEV — altitude deviation on BlueWalker 3
 *   2. HIGH REG-UNU — unscheduled FCC filing (SCS modification)
 *   3. LOW ORB-MAN — routine station-keeping maneuver on BB-7
 */
export function generateMockSignals(): Signal[] {
  const now = new Date().toISOString();
  const thirtyMinAgo = new Date(Date.now() - 30 * 60_000).toISOString();
  const twoHoursAgo = new Date(Date.now() - 2 * 3600_000).toISOString();

  return [
    // ── 1. CRITICAL ORB-DEV: BlueWalker 3 altitude drop ──────────────
    {
      id: "mock-signal-001",
      anomaly_type: _ORB_DEV,
      severity: _CRITICAL,
      entity_id: ENTITY_ID_BW3,
      entity_type: "satellite",
      entity_name: "BlueWalker 3 (BW3)",
      metric_type: "altitude_km",
      observed_value: 498.3,
      baseline_value: 507.1,
      z_score: -6.42,
      raw_data: {
        norad_id: "53807",
        epoch: thirtyMinAgo,
        delta_km: -8.8,
        bstar: 0.000118,
        bstar_baseline: 0.000042,
        source_tle: "space-track",
        consecutive_drops: 3,
        note: "Altitude 8.8 km below 30-day baseline. BSTAR 2.8x elevated — possible atmospheric drag anomaly or unannounced orbit-lowering maneuver.",
      },
      source: "tle-health-monitor",
      processed: false,
      briefing_id: null,
      detected_at: thirtyMinAgo,
      created_at: thirtyMinAgo,
    },

    // ── 2. HIGH REG-UNU: Unscheduled FCC SCS filing ──────────────────
    {
      id: "mock-signal-002",
      anomaly_type: _REG_UNU,
      severity: _HIGH,
      entity_id: ENTITY_ID_ASTS,
      entity_type: "company",
      entity_name: "AST SpaceMobile",
      metric_type: "fcc_filing_frequency",
      observed_value: 4,
      baseline_value: 1.2,
      z_score: 3.89,
      raw_data: {
        docket: "25-201",
        filing_type: "SCS Modification Application",
        filer: "AST SpaceMobile",
        filed_date: now.split("T")[0],
        filing_system: "ECFS",
        title: "Amendment to Supplemental Coverage from Space Authorization — Expanded Band Plan and Power Limits",
        exhibit_count: 7,
        note: "Unscheduled modification to SCS authorization requesting expanded spectrum allocation and revised EIRP limits for Block 2 constellation.",
      },
      source: "ecfs-monitor",
      processed: false,
      briefing_id: null,
      detected_at: twoHoursAgo,
      created_at: twoHoursAgo,
    },

    // ── 3. LOW ORB-MAN: Routine BB-7 station-keeping ─────────────────
    {
      id: "mock-signal-003",
      anomaly_type: _ORB_MAN,
      severity: _LOW,
      entity_id: ENTITY_ID_BW7,
      entity_type: "satellite",
      entity_name: "BlueBird 7 (BB-7)",
      metric_type: "mean_motion_rev_day",
      observed_value: 15.1948,
      baseline_value: 15.1923,
      z_score: 1.12,
      raw_data: {
        norad_id: "62401",
        epoch: twoHoursAgo,
        delta_rev_day: 0.0025,
        maneuver_type: "station_keeping",
        source_tle: "celestrak",
        estimated_delta_v_ms: 0.18,
        note: "Minor mean-motion adjustment consistent with routine station-keeping. Within nominal operational envelope.",
      },
      source: "tle-health-monitor",
      processed: false,
      briefing_id: null,
      detected_at: twoHoursAgo,
      created_at: twoHoursAgo,
    },
  ];
}
