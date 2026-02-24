/**
 * API Route: Refresh TLE data from CelesTrak + Space-Track (dual-source)
 * POST /api/cron/tle-refresh
 *
 * Fetches from BOTH sources independently every cron run:
 * - CelesTrak: Supplemental GP data (third-party platform, fits own GP elements
 *   from operator-informed positions). Better positional accuracy, but GP fitting
 *   introduces BSTAR volatility artifacts. Primary for position.
 * - Space-Track: US Space Force SSN radar tracking. Independent source with
 *   smoother BSTAR output. Primary for drag trend analysis.
 *
 * Each data point is tagged with its source. CelesTrak is preferred for
 * the satellites table (positional state). Both always write to tle_history.
 *
 * Called by Vercel cron every 4 hours.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createApiHandler } from '@/lib/api/handler';
import { getServiceClient } from '@/lib/supabase';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

// ASTS Constellation - ordered newest to oldest
const ASTS_SATELLITES: Record<string, { name: string; launch: string }> = {
  '67232': { name: 'BLUEWALKER 3-FM1', launch: '2025-01-14' },
  '61046': { name: 'BLUEBIRD 5', launch: '2024-09-12' },
  '61049': { name: 'BLUEBIRD 4', launch: '2024-09-12' },
  '61045': { name: 'BLUEBIRD 3', launch: '2024-09-12' },
  '61048': { name: 'BLUEBIRD 2', launch: '2024-09-12' },
  '61047': { name: 'BLUEBIRD 1', launch: '2024-09-12' },
  '53807': { name: 'BLUEWALKER 3', launch: '2022-09-10' },
};

const NORAD_IDS = Object.keys(ASTS_SATELLITES);

// CelesTrak supplemental GP — third-party platform, fits GP elements from operator-informed positions
const CELESTRAK_GP_JSON = 'https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=ast&FORMAT=json';
const CELESTRAK_GP_TLE = 'https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=ast&FORMAT=tle';

// Space-Track config
const SPACE_TRACK_BASE = 'https://www.space-track.org';
const SPACE_TRACK_USER = process.env.SPACE_TRACK_USERNAME || '';
const SPACE_TRACK_PASS = process.env.SPACE_TRACK_PASSWORD || '';

// Space-Track session
let sessionCookie: string | null = null;

interface GPData {
  NORAD_CAT_ID: string;
  OBJECT_NAME: string;
  EPOCH: string;
  TLE_LINE0: string;
  TLE_LINE1: string;
  TLE_LINE2: string;
  BSTAR: string;
  MEAN_MOTION: string;
  MEAN_MOTION_DOT: string;
  MEAN_MOTION_DDOT: string;
  INCLINATION: string;
  ECCENTRICITY: string;
  RA_OF_ASC_NODE: string;
  ARG_OF_PERICENTER: string;
  MEAN_ANOMALY: string;
  SEMIMAJOR_AXIS: string;
  PERIOD: string;
  APOAPSIS: string;
  PERIAPSIS: string;
  REV_AT_EPOCH: string;
  OBJECT_TYPE: string;
  RCS_SIZE: string;
  COUNTRY_CODE: string;
  LAUNCH_DATE: string;
  DECAY_DATE: string | null;
  _source?: string; // 'celestrak' or 'spacetrack'
}

// CelesTrak JSON response shape
interface CelestrakGP {
  OBJECT_NAME: string;
  OBJECT_ID: string;
  EPOCH: string;
  MEAN_MOTION: number;
  ECCENTRICITY: number;
  INCLINATION: number;
  RA_OF_ASC_NODE: number;
  ARG_OF_PERICENTER: number;
  MEAN_ANOMALY: number;
  EPHEMERIS_TYPE: number;
  CLASSIFICATION_TYPE: string;
  NORAD_CAT_ID: number;
  ELEMENT_SET_NO: number;
  REV_AT_EPOCH: number;
  BSTAR: number;
  MEAN_MOTION_DOT: number;
  MEAN_MOTION_DDOT: number;
  DATA_SOURCE?: string;
}

const SATELLITE_FRIENDLY_NAMES: Record<string, string> = {
  '67232': 'FM1',
  '61046': 'BB5',
  '61049': 'BB4',
  '61045': 'BB3',
  '61048': 'BB2',
  '61047': 'BB1',
  '53807': 'BW3',
};

interface HealthAnomaly {
  noradId: string;
  name: string;
  type: 'altitude_drop' | 'drag_spike' | 'stale_tle' | 'orbit_raise';
  severity: 'medium' | 'high' | 'critical';
  description: string;
  metrics: Record<string, number | string>;
}

interface ManeuverEvent {
  noradId: string;
  name: string;
  type: 'orbit_raise' | 'orbit_lower' | 'plane_change';
  severity: 'high' | 'medium' | 'low';
  description: string;
  epoch: string;
  metrics: Record<string, number | string>;
}

async function detectHealthAnomalies(
  supabase: any,
  currentData: GPData[]
): Promise<HealthAnomaly[]> {
  const anomalies: HealthAnomaly[] = [];
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  // Batch fetch: single query for all satellites' 7-day history
  // CRITICAL: Filter to spacetrack source only — CelesTrak GP fitting introduces
  // BSTAR volatility artifacts and altitude noise that cause false anomaly detections.
  // Space-Track (SSN radar) provides smoother, more reliable trend data.
  const noradIds = currentData.map(gp => String(gp.NORAD_CAT_ID));
  const { data: allHistory } = await supabase
    .from('tle_history')
    .select('norad_id, epoch, apoapsis_km, periapsis_km, bstar, mean_motion')
    .in('norad_id', noradIds)
    .eq('source', 'spacetrack')
    .gte('epoch', sevenDaysAgo)
    .order('epoch', { ascending: true })
    .limit(350);

  // Group history by norad_id
  const historyByNorad = new Map<string, any[]>();
  for (const row of (allHistory || [])) {
    const arr = historyByNorad.get(row.norad_id) || [];
    arr.push(row);
    historyByNorad.set(row.norad_id, arr);
  }

  // Safe float parser — returns null instead of NaN for any non-numeric input
  const sf = (v: any): number | null => {
    if (v == null || v === '') return null;
    const n = parseFloat(String(v));
    return isNaN(n) ? null : n;
  };

  for (const gp of currentData) {
    const noradId = String(gp.NORAD_CAT_ID);
    const name = SATELLITE_FRIENDLY_NAMES[noradId] || gp.OBJECT_NAME;
    const currentApoapsis = sf(gp.APOAPSIS);
    const currentPeriapsis = sf(gp.PERIAPSIS);
    const currentAlt = currentApoapsis != null && currentPeriapsis != null
      ? (currentApoapsis + currentPeriapsis) / 2 : null;
    const currentBstar = sf(gp.BSTAR);

    const history = historyByNorad.get(noradId);

    if (!history || history.length < 2) continue;

    const oldest = history[0] as any;
    const oldestApoapsis = sf(oldest.apoapsis_km);
    const oldestPeriapsis = sf(oldest.periapsis_km);
    const oldestAlt = oldestApoapsis != null && oldestPeriapsis != null
      ? (oldestApoapsis + oldestPeriapsis) / 2 : null;
    const altDelta = currentAlt != null && oldestAlt != null ? currentAlt - oldestAlt : null;
    const oldestBstar = sf(oldest.bstar);
    const bstarDelta = currentBstar != null && oldestBstar != null ? currentBstar - oldestBstar : null;

    // Check TLE staleness
    const epochDate = new Date(gp.EPOCH);
    const tleAgeHours = (Date.now() - epochDate.getTime()) / (1000 * 60 * 60);
    if (tleAgeHours > 336) { // 14 days
      anomalies.push({
        noradId, name,
        type: 'stale_tle',
        severity: 'high',
        description: `${name} TLE is ${Math.round(tleAgeHours / 24)} days stale — no tracking updates from CelesTrak/Space-Track`,
        metrics: { tle_age_hours: Math.round(tleAgeHours), last_epoch: gp.EPOCH },
      });
    }

    // Check altitude drop (>5km in 7 days = warning, >15km = critical)
    if (altDelta != null && currentAlt != null) {
      if (altDelta < -15) {
        anomalies.push({
          noradId, name,
          type: 'altitude_drop',
          severity: 'critical',
          description: `${name} altitude dropped ${Math.abs(altDelta).toFixed(1)} km in 7 days — potential deorbit or anomaly`,
          metrics: { altitude_delta_km: Math.round(altDelta * 100) / 100, current_alt_km: Math.round(currentAlt * 10) / 10 },
        });
      } else if (altDelta < -5) {
        anomalies.push({
          noradId, name,
          type: 'altitude_drop',
          severity: 'medium',
          description: `${name} altitude dropped ${Math.abs(altDelta).toFixed(1)} km in 7 days — elevated atmospheric drag`,
          metrics: { altitude_delta_km: Math.round(altDelta * 100) / 100, current_alt_km: Math.round(currentAlt * 10) / 10 },
        });
      }

      // Check orbit raise (>5km in 7 days — likely maneuver)
      if (altDelta > 5) {
        anomalies.push({
          noradId, name,
          type: 'orbit_raise',
          severity: 'medium',
          description: `${name} altitude raised ${altDelta.toFixed(1)} km in 7 days — possible orbit raise maneuver`,
          metrics: { altitude_delta_km: Math.round(altDelta * 100) / 100, current_alt_km: Math.round(currentAlt * 10) / 10 },
        });
      }
    }

    // Check drag coefficient spike (B* increase > 0.001)
    if (bstarDelta != null && currentBstar != null) {
      if (Math.abs(bstarDelta) > 0.001) {
        const direction = bstarDelta > 0 ? 'increased' : 'decreased';
        anomalies.push({
          noradId, name,
          type: 'drag_spike',
          severity: 'medium',
          description: `${name} drag coefficient ${direction} significantly: B* Δ${bstarDelta.toExponential(2)}`,
          metrics: { bstar_current: currentBstar, bstar_delta: bstarDelta },
        });
      }
    }
  }

  return anomalies;
}

async function createHealthSignals(
  supabase: any,
  anomalies: HealthAnomaly[]
): Promise<number> {
  let created = 0;
  const now = new Date().toISOString();
  const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(); // 7 day expiry

  for (const anomaly of anomalies) {
    // Fingerprint: type + satellite + week (allow re-fire weekly)
    const weekKey = new Date().toISOString().substring(0, 10); // YYYY-MM-DD granularity daily
    const fp = `${anomaly.type}_${anomaly.noradId}_${weekKey}`;
    const hash = Array.from(new Uint8Array(
      await crypto.subtle.digest('SHA-256', new TextEncoder().encode(fp))
    )).map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 32);

    // Check dedup
    const { data: existing } = await supabase
      .from('signals')
      .select('id')
      .eq('fingerprint', hash)
      .limit(1);

    if (existing && existing.length > 0) continue;

    const { error } = await supabase
      .from('signals')
      .insert({
        signal_type: 'constellation_health',
        severity: anomaly.severity,
        title: anomaly.description,
        description: `Automated health anomaly detected for ${anomaly.name} (NORAD ${anomaly.noradId}). Type: ${anomaly.type}.`,
        source_refs: [{ table: 'satellites', id: anomaly.noradId, title: anomaly.name, date: now.split('T')[0] }],
        metrics: anomaly.metrics,
        fingerprint: hash,
        status: 'active',
        detected_at: now,
        expires_at: expires,
      });

    if (!error) {
      created++;
      console.log(`[TLE] SIGNAL: ${anomaly.severity.toUpperCase()} — ${anomaly.description}`);
    }
  }

  return created;
}

// ============================================================================
// Maneuver Detection — server-side (Thread 006 GAP 1)
// Uses CelesTrak data (primary for positional accuracy & maneuver detection).
// Algorithm: 2σ outlier detection on mean motion deltas (same as client-side
// lib/orbital/maneuver-detection.ts but persists results to signals table).
// ============================================================================

const INCLINATION_THRESHOLD_DEG = 0.02; // Above CelesTrak GP fitting noise (0.003-0.01°)

async function detectManeuvers(
  supabase: any
): Promise<ManeuverEvent[]> {
  const maneuvers: ManeuverEvent[] = [];
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  // Fetch 30 days of CelesTrak TLE history for all tracked satellites
  const noradIds = Object.keys(SATELLITE_FRIENDLY_NAMES);
  const { data: allHistory } = await supabase
    .from('tle_history')
    .select('norad_id, epoch, mean_motion, inclination, apoapsis_km, periapsis_km')
    .in('norad_id', noradIds)
    .eq('source', 'celestrak')
    .gte('epoch', thirtyDaysAgo)
    .order('epoch', { ascending: true })
    .limit(2000);

  if (!allHistory || allHistory.length === 0) return [];

  // Group by satellite
  const historyByNorad = new Map<string, any[]>();
  for (const row of allHistory) {
    const arr = historyByNorad.get(row.norad_id) || [];
    arr.push(row);
    historyByNorad.set(row.norad_id, arr);
  }

  const sf = (v: any): number | null => {
    if (v == null || v === '') return null;
    const n = parseFloat(String(v));
    return isNaN(n) ? null : n;
  };

  for (const [noradId, history] of Array.from(historyByNorad.entries())) {
    const name = SATELLITE_FRIENDLY_NAMES[noradId] || noradId;
    if (history.length < 10) continue;

    // Mean motion analysis — 2σ outlier detection
    const mm = history.map((d: any) => sf(d.mean_motion));
    const diffs: (number | null)[] = [null];
    for (let i = 1; i < mm.length; i++) {
      if (mm[i] != null && mm[i - 1] != null) {
        diffs.push(mm[i]! - mm[i - 1]!);
      } else {
        diffs.push(null);
      }
    }

    const validDiffs = diffs.filter((d): d is number => d != null);
    if (validDiffs.length < 5) continue;

    const mean = validDiffs.reduce((a, b) => a + b, 0) / validDiffs.length;
    const variance = validDiffs.reduce((a, b) => a + (b - mean) ** 2, 0) / validDiffs.length;
    const std = Math.sqrt(variance);
    if (std === 0) continue;

    const threshold = 2 * std;
    const windowSize = 5;
    let lastManeuverIdx = -windowSize;

    // Only look at maneuvers in the last 7 days (avoid re-detecting old ones)
    const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;

    for (let i = 1; i < diffs.length; i++) {
      const diff = diffs[i];
      if (diff == null) continue;
      if (i - lastManeuverIdx < windowSize) continue;

      const epochTime = new Date(history[i].epoch).getTime();
      if (epochTime < sevenDaysAgo) continue;

      if (Math.abs(diff - mean) > threshold) {
        // Mean motion decrease = orbit raise, increase = orbit lower
        const type = diff > 0 ? 'orbit_lower' as const : 'orbit_raise' as const;

        // Calculate altitude delta for context
        const apoCur = sf(history[i].apoapsis_km);
        const periCur = sf(history[i].periapsis_km);
        const apoPrev = sf(history[i - 1].apoapsis_km);
        const periPrev = sf(history[i - 1].periapsis_km);
        const altCur = apoCur != null && periCur != null ? (apoCur + periCur) / 2 : null;
        const altPrev = apoPrev != null && periPrev != null ? (apoPrev + periPrev) / 2 : null;
        const altDelta = altCur != null && altPrev != null ? altCur - altPrev : null;

        const verb = type === 'orbit_raise' ? 'Orbit raise' : 'Orbit lowering';
        const altStr = altDelta != null ? ` (${altDelta > 0 ? '+' : ''}${altDelta.toFixed(1)} km)` : '';
        const severity = type === 'orbit_raise' ? 'high' as const : 'medium' as const;

        maneuvers.push({
          noradId, name, type, severity,
          epoch: history[i].epoch,
          description: `${name} ${verb} detected${altStr}`,
          metrics: {
            mean_motion_delta: Math.round(diff * 10000) / 10000,
            altitude_delta_km: altDelta != null ? Math.round(altDelta * 10) / 10 : 'N/A',
            current_alt_km: altCur != null ? Math.round(altCur * 10) / 10 : 'N/A',
          },
        });
        lastManeuverIdx = i;
      }
    }

    // Inclination analysis — plane changes
    const incl = history.map((d: any) => sf(d.inclination));
    const inclDiffs: (number | null)[] = [null];
    for (let i = 1; i < incl.length; i++) {
      if (incl[i] != null && incl[i - 1] != null) {
        inclDiffs.push(incl[i]! - incl[i - 1]!);
      } else {
        inclDiffs.push(null);
      }
    }

    const validInclDiffs = inclDiffs.filter((d): d is number => d != null);
    if (validInclDiffs.length >= 5) {
      const inclMean = validInclDiffs.reduce((a, b) => a + b, 0) / validInclDiffs.length;
      const inclVar = validInclDiffs.reduce((a, b) => a + (b - inclMean) ** 2, 0) / validInclDiffs.length;
      const inclStd = Math.sqrt(inclVar);

      if (inclStd > 0) {
        const inclThreshold = 2 * inclStd;
        let lastPlaneIdx = -windowSize;
        for (let i = 1; i < inclDiffs.length; i++) {
          const diff = inclDiffs[i];
          if (diff == null) continue;
          if (i - lastPlaneIdx < windowSize) continue;

          const epochTime = new Date(history[i].epoch).getTime();
          if (epochTime < sevenDaysAgo) continue;

          if (Math.abs(diff - inclMean) > inclThreshold && Math.abs(diff) > INCLINATION_THRESHOLD_DEG) {
            const alreadyFlagged = maneuvers.some(m => m.noradId === noradId && Math.abs(new Date(m.epoch).getTime() - epochTime) < 24 * 60 * 60 * 1000);
            if (!alreadyFlagged) {
              maneuvers.push({
                noradId, name,
                type: 'plane_change',
                severity: 'high',
                epoch: history[i].epoch,
                description: `${name} plane change detected: Δi = ${diff > 0 ? '+' : ''}${diff.toFixed(4)}°`,
                metrics: {
                  inclination_delta_deg: Math.round(diff * 10000) / 10000,
                  current_inclination_deg: incl[i] != null ? Math.round(incl[i]! * 100) / 100 : 'N/A',
                },
              });
              lastPlaneIdx = i;
            }
          }
        }
      }
    }
  }

  return maneuvers;
}

async function createManeuverSignals(
  supabase: any,
  maneuvers: ManeuverEvent[]
): Promise<number> {
  let created = 0;
  const now = new Date().toISOString();
  const expires = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(); // 14 day expiry

  for (const maneuver of maneuvers) {
    const dateKey = maneuver.epoch.substring(0, 10);
    const fp = `maneuver_${maneuver.type}_${maneuver.noradId}_${dateKey}`;
    const hash = Array.from(new Uint8Array(
      await crypto.subtle.digest('SHA-256', new TextEncoder().encode(fp))
    )).map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 32);

    const { data: existing } = await supabase
      .from('signals')
      .select('id')
      .eq('fingerprint', hash)
      .limit(1);

    if (existing && existing.length > 0) continue;

    const { error } = await supabase
      .from('signals')
      .insert({
        signal_type: 'orbital_maneuver',
        severity: maneuver.severity,
        category: 'constellation',
        title: maneuver.description,
        description: `Maneuver detected for ${maneuver.name} (NORAD ${maneuver.noradId}) at epoch ${maneuver.epoch}. Type: ${maneuver.type}. Statistical outlier in mean motion/inclination time series (2σ threshold, CelesTrak source).`,
        source_refs: [{ table: 'satellites', id: maneuver.noradId, title: maneuver.name, date: maneuver.epoch.split('T')[0] }],
        metrics: maneuver.metrics,
        fingerprint: hash,
        status: 'active',
        detected_at: maneuver.epoch,
        expires_at: expires,
      });

    if (!error) {
      created++;
      console.log(`[TLE] MANEUVER: ${maneuver.severity.toUpperCase()} — ${maneuver.description}`);
    }
  }

  return created;
}

// ============================================================================
// CelesTrak — primary for position (supplemental GP, no auth)
// ============================================================================

function parseTLEText(text: string): Record<string, { line0: string; line1: string; line2: string }> {
  const result: Record<string, { line0: string; line1: string; line2: string }> = {};
  const lines = text.trim().split('\n').map(l => l.trim()).filter(l => l);

  for (let i = 0; i < lines.length; i += 3) {
    if (i + 2 >= lines.length) break;
    const line0 = lines[i];
    const line1 = lines[i + 1];
    const line2 = lines[i + 2];

    if (line1.startsWith('1 ')) {
      const noradId = line1.substring(2, 7).trim();
      result[noradId] = { line0: `0 ${line0}`, line1, line2 };
    }
  }

  return result;
}

async function fetchCelestrakGP(): Promise<GPData[]> {
  console.log('[TLE] Fetching CelesTrak supplemental GP...');

  // Fetch JSON (orbital elements) and TLE (formatted lines) in parallel
  const [jsonRes, tleRes] = await Promise.all([
    fetch(CELESTRAK_GP_JSON, { signal: AbortSignal.timeout(15000) }),
    fetch(CELESTRAK_GP_TLE, { signal: AbortSignal.timeout(15000) }),
  ]);

  if (!jsonRes.ok || !tleRes.ok) {
    throw new Error(`CelesTrak fetch failed: JSON=${jsonRes.status}, TLE=${tleRes.status}`);
  }

  const jsonData: CelestrakGP[] = await jsonRes.json();
  const tleText = await tleRes.text();
  const tleLines = parseTLEText(tleText);

  const MU = 398600.8;    // WGS-72 (matches SGP4 TLE generation standard)
  const RE = 6378.137;    // Earth radius (km)

  const gpData: GPData[] = jsonData
    .filter(ct => {
      const id = String(ct.NORAD_CAT_ID);
      return NORAD_IDS.includes(id);
    })
    .map(ct => {
      const noradId = String(ct.NORAD_CAT_ID);
      const tle = tleLines[noradId];

      // Derive orbital parameters from mean motion
      const n = ct.MEAN_MOTION; // rev/day
      const nRadSec = n * 2 * Math.PI / 86400; // rad/s
      const a = Math.pow(MU / (nRadSec * nRadSec), 1 / 3); // semi-major axis (km)
      const ecc = ct.ECCENTRICITY;
      const period = 1440.0 / n; // minutes
      const apoapsis = a * (1 + ecc) - RE;
      const periapsis = a * (1 - ecc) - RE;

      return {
        NORAD_CAT_ID: noradId,
        OBJECT_NAME: ct.OBJECT_NAME,
        EPOCH: ct.EPOCH,
        TLE_LINE0: tle?.line0 || `0 ${ct.OBJECT_NAME}`,
        TLE_LINE1: tle?.line1 || '',
        TLE_LINE2: tle?.line2 || '',
        BSTAR: String(ct.BSTAR),
        MEAN_MOTION: String(ct.MEAN_MOTION),
        MEAN_MOTION_DOT: String(ct.MEAN_MOTION_DOT),
        MEAN_MOTION_DDOT: String(ct.MEAN_MOTION_DDOT),
        INCLINATION: String(ct.INCLINATION),
        ECCENTRICITY: String(ct.ECCENTRICITY),
        RA_OF_ASC_NODE: String(ct.RA_OF_ASC_NODE),
        ARG_OF_PERICENTER: String(ct.ARG_OF_PERICENTER),
        MEAN_ANOMALY: String(ct.MEAN_ANOMALY),
        SEMIMAJOR_AXIS: String(a.toFixed(3)),
        PERIOD: String(period.toFixed(4)),
        APOAPSIS: String(apoapsis.toFixed(3)),
        PERIAPSIS: String(periapsis.toFixed(3)),
        REV_AT_EPOCH: String(ct.REV_AT_EPOCH),
        OBJECT_TYPE: 'PAYLOAD',
        RCS_SIZE: 'LARGE',
        COUNTRY_CODE: 'US',
        LAUNCH_DATE: ASTS_SATELLITES[noradId]?.launch || '',
        DECAY_DATE: null,
        _source: 'celestrak',
      };
    });

  console.log(`[TLE] CelesTrak returned ${gpData.length} AST satellites`);

  if (gpData.length === 0) {
    throw new Error('CelesTrak returned no matching satellites');
  }

  return gpData;
}

// ============================================================================
// Space-Track — secondary source (SSN radar tracking, requires auth)
// ============================================================================

async function spaceTrackLogin(): Promise<string> {
  if (!SPACE_TRACK_USER || !SPACE_TRACK_PASS) {
    throw new Error('SPACE_TRACK_USERNAME and SPACE_TRACK_PASSWORD must be set');
  }

  console.log(`[TLE] Logging into Space-Track as ${SPACE_TRACK_USER.substring(0, 5)}...`);

  const response = await fetch(`${SPACE_TRACK_BASE}/ajaxauth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      identity: SPACE_TRACK_USER,
      password: SPACE_TRACK_PASS,
    }),
  });

  if (!response.ok) {
    throw new Error(`Space-Track login failed: ${response.status}`);
  }

  const cookies = response.headers.get('set-cookie');
  if (!cookies || !cookies.includes('chocolatechip=')) {
    throw new Error('No session cookie received from Space-Track');
  }

  const match = cookies.match(/chocolatechip=([^;]+)/);
  if (!match) {
    throw new Error('Failed to parse Space-Track session cookie');
  }

  sessionCookie = `chocolatechip=${match[1]}`;
  console.log('[TLE] Space-Track login successful');
  return sessionCookie;
}

async function spaceTrackRequest(endpoint: string): Promise<GPData[]> {
  if (!sessionCookie) {
    await spaceTrackLogin();
  }

  const url = `${SPACE_TRACK_BASE}${endpoint}`;
  console.log(`[TLE] Fetching: ${endpoint.substring(0, 80)}...`);

  const response = await fetch(url, {
    headers: { Cookie: sessionCookie! },
  });

  if (response.status === 401) {
    console.log('[TLE] Session expired, re-authenticating...');
    sessionCookie = null;
    await spaceTrackLogin();
    return spaceTrackRequest(endpoint);
  }

  if (!response.ok) {
    throw new Error(`Space-Track request failed: ${response.status}`);
  }

  const data = await response.json();
  console.log(`[TLE] Received ${data.length} records`);
  return data.map((d: any) => ({ ...d, _source: 'spacetrack' }));
}

async function fetchSpaceTrackGP(): Promise<GPData[]> {
  const idsStr = NORAD_IDS.join(',');
  const endpoint = `/basicspacedata/query/class/gp/NORAD_CAT_ID/${idsStr}/orderby/EPOCH%20desc/format/json`;
  return spaceTrackRequest(endpoint);
}

// ============================================================================
// Main handler
// ============================================================================

function safeInt(value: string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? null : parsed;
}

interface SourceResult {
  noradId: string;
  name: string;
  epoch: string;
  source: string;
  historyAdded: boolean;
}

export const POST = createApiHandler({
  auth: 'cron',
  handler: async (request) => {
    const startTime = Date.now();
    const supabase = getServiceClient();

    // Fetch BOTH sources independently
    let celestrakData: GPData[] = [];
    let spacetrackData: GPData[] = [];
    let celestrakError: string | null = null;
    let spacetrackError: string | null = null;

    // Launch both fetches in parallel
    const [celestrakResult, spacetrackResult] = await Promise.allSettled([
      fetchCelestrakGP(),
      (SPACE_TRACK_USER && SPACE_TRACK_PASS)
        ? fetchSpaceTrackGP()
        : Promise.reject(new Error('No Space-Track credentials')),
    ]);

    if (celestrakResult.status === 'fulfilled') {
      celestrakData = celestrakResult.value;
      console.log(`[TLE] CelesTrak: ${celestrakData.length} satellites`);
    } else {
      celestrakError = String(celestrakResult.reason);
      console.warn('[TLE] CelesTrak failed:', celestrakError);
    }

    if (spacetrackResult.status === 'fulfilled') {
      spacetrackData = spacetrackResult.value;
      console.log(`[TLE] Space-Track: ${spacetrackData.length} satellites`);
    } else {
      spacetrackError = String(spacetrackResult.reason);
      console.warn('[TLE] Space-Track failed:', spacetrackError);
    }

    // If both failed, return error
    if (celestrakData.length === 0 && spacetrackData.length === 0) {
      return NextResponse.json(
        {
          error: 'Both sources failed',
          celestrakError,
          spacetrackError,
        },
        { status: 500 }
      );
    }

    const results: SourceResult[] = [];
    const celestrakNoradIds = new Set<string>();

    // Process CelesTrak data first (preferred for satellites table)
    for (const gp of celestrakData) {
      const noradId = String(gp.NORAD_CAT_ID);
      const name = (gp.OBJECT_NAME || '').trim();
      const epoch = (gp.EPOCH || '').substring(0, 19);
      celestrakNoradIds.add(noradId);

      console.log(`[TLE] Processing ${name} (${noradId}): epoch ${epoch} [celestrak]`);

      // CelesTrak always upserts satellites table (preferred source)
      const satelliteData = {
        norad_id: noradId,
        name: name,
        tle_line0: gp.TLE_LINE0,
        tle_line1: gp.TLE_LINE1,
        tle_line2: gp.TLE_LINE2,
        tle_epoch: gp.EPOCH,
        bstar: gp.BSTAR,
        mean_motion: gp.MEAN_MOTION,
        mean_motion_dot: gp.MEAN_MOTION_DOT,
        mean_motion_ddot: gp.MEAN_MOTION_DDOT,
        inclination: gp.INCLINATION,
        eccentricity: gp.ECCENTRICITY,
        ra_of_asc_node: gp.RA_OF_ASC_NODE,
        arg_of_pericenter: gp.ARG_OF_PERICENTER,
        mean_anomaly: gp.MEAN_ANOMALY,
        semimajor_axis: gp.SEMIMAJOR_AXIS,
        period_minutes: gp.PERIOD,
        apoapsis_km: gp.APOAPSIS,
        periapsis_km: gp.PERIAPSIS,
        rev_at_epoch: safeInt(gp.REV_AT_EPOCH),
        object_type: gp.OBJECT_TYPE,
        rcs_size: gp.RCS_SIZE,
        country_code: gp.COUNTRY_CODE,
        launch_date: gp.LAUNCH_DATE,
        decay_date: gp.DECAY_DATE,
        tle_source: 'celestrak',
        raw_gp: gp,
        updated_at: new Date().toISOString(),
      };

      const { error: upsertError } = await supabase
        .from('satellites')
        .upsert(satelliteData, { onConflict: 'norad_id' });

      if (upsertError) {
        console.error(`[TLE] Error upserting satellite ${noradId}:`, upsertError);
      }

      // Insert into TLE history with source tag
      const historyData = {
        norad_id: noradId,
        epoch: gp.EPOCH,
        tle_line0: gp.TLE_LINE0,
        tle_line1: gp.TLE_LINE1,
        tle_line2: gp.TLE_LINE2,
        bstar: gp.BSTAR,
        mean_motion: gp.MEAN_MOTION,
        mean_motion_dot: gp.MEAN_MOTION_DOT,
        apoapsis_km: gp.APOAPSIS,
        periapsis_km: gp.PERIAPSIS,
        eccentricity: gp.ECCENTRICITY,
        inclination: gp.INCLINATION,
        ra_of_asc_node: gp.RA_OF_ASC_NODE,
        arg_of_pericenter: gp.ARG_OF_PERICENTER,
        mean_anomaly: gp.MEAN_ANOMALY,
        semimajor_axis: gp.SEMIMAJOR_AXIS,
        period_minutes: gp.PERIOD,
        rev_at_epoch: safeInt(gp.REV_AT_EPOCH),
        source: 'celestrak',
        raw_gp: gp,
      };

      const { error: historyError } = await supabase
        .from('tle_history')
        .insert(historyData);

      const historyAdded = !historyError || historyError.code !== '23505';

      if (historyError && historyError.code !== '23505') {
        console.error(`[TLE] Error inserting history for ${noradId} [celestrak]:`, historyError);
      }

      results.push({ noradId, name, epoch, source: 'celestrak', historyAdded });
    }

    // Process Space-Track data
    for (const gp of spacetrackData) {
      const noradId = String(gp.NORAD_CAT_ID);
      const name = (gp.OBJECT_NAME || '').trim();
      const epoch = (gp.EPOCH || '').substring(0, 19);

      console.log(`[TLE] Processing ${name} (${noradId}): epoch ${epoch} [spacetrack]`);

      // Only upsert satellites table if CelesTrak didn't have this satellite
      if (!celestrakNoradIds.has(noradId)) {
        const satelliteData = {
          norad_id: noradId,
          name: name,
          tle_line0: gp.TLE_LINE0,
          tle_line1: gp.TLE_LINE1,
          tle_line2: gp.TLE_LINE2,
          tle_epoch: gp.EPOCH,
          bstar: gp.BSTAR,
          mean_motion: gp.MEAN_MOTION,
          mean_motion_dot: gp.MEAN_MOTION_DOT,
          mean_motion_ddot: gp.MEAN_MOTION_DDOT,
          inclination: gp.INCLINATION,
          eccentricity: gp.ECCENTRICITY,
          ra_of_asc_node: gp.RA_OF_ASC_NODE,
          arg_of_pericenter: gp.ARG_OF_PERICENTER,
          mean_anomaly: gp.MEAN_ANOMALY,
          semimajor_axis: gp.SEMIMAJOR_AXIS,
          period_minutes: gp.PERIOD,
          apoapsis_km: gp.APOAPSIS,
          periapsis_km: gp.PERIAPSIS,
          rev_at_epoch: safeInt(gp.REV_AT_EPOCH),
          object_type: gp.OBJECT_TYPE,
          rcs_size: gp.RCS_SIZE,
          country_code: gp.COUNTRY_CODE,
          launch_date: gp.LAUNCH_DATE,
          decay_date: gp.DECAY_DATE,
          tle_source: 'spacetrack',
          raw_gp: gp,
          updated_at: new Date().toISOString(),
        };

        const { error: upsertError } = await supabase
          .from('satellites')
          .upsert(satelliteData, { onConflict: 'norad_id' });

        if (upsertError) {
          console.error(`[TLE] Error upserting satellite ${noradId}:`, upsertError);
        }
      }

      // Always insert into TLE history (unique constraint now includes source)
      const historyData = {
        norad_id: noradId,
        epoch: gp.EPOCH,
        tle_line0: gp.TLE_LINE0,
        tle_line1: gp.TLE_LINE1,
        tle_line2: gp.TLE_LINE2,
        bstar: gp.BSTAR,
        mean_motion: gp.MEAN_MOTION,
        mean_motion_dot: gp.MEAN_MOTION_DOT,
        apoapsis_km: gp.APOAPSIS,
        periapsis_km: gp.PERIAPSIS,
        eccentricity: gp.ECCENTRICITY,
        inclination: gp.INCLINATION,
        ra_of_asc_node: gp.RA_OF_ASC_NODE,
        arg_of_pericenter: gp.ARG_OF_PERICENTER,
        mean_anomaly: gp.MEAN_ANOMALY,
        semimajor_axis: gp.SEMIMAJOR_AXIS,
        period_minutes: gp.PERIOD,
        rev_at_epoch: safeInt(gp.REV_AT_EPOCH),
        source: 'spacetrack',
        raw_gp: gp,
      };

      const { error: historyError } = await supabase
        .from('tle_history')
        .insert(historyData);

      const historyAdded = !historyError || historyError.code !== '23505';

      if (historyError && historyError.code !== '23505') {
        console.error(`[TLE] Error inserting history for ${noradId} [spacetrack]:`, historyError);
      }

      results.push({ noradId, name, epoch, source: 'spacetrack', historyAdded });
    }

    const duration = Date.now() - startTime;
    const celestrakNew = results.filter(r => r.source === 'celestrak' && r.historyAdded).length;
    const spacetrackNew = results.filter(r => r.source === 'spacetrack' && r.historyAdded).length;

    console.log(`[TLE] Sync complete: CT=${celestrakData.length}(${celestrakNew} new) ST=${spacetrackData.length}(${spacetrackNew} new) ${duration}ms`);

    // Run health anomaly detection on Space-Track data (smoother BSTAR/altitude trends).
    // CelesTrak GP fitting artifacts cause false altitude drops and drag spikes.
    let healthSignals = 0;
    const healthData = spacetrackData.length > 0 ? spacetrackData : celestrakData;
    if (spacetrackData.length === 0 && celestrakData.length > 0) {
      console.warn('[tle-refresh] Space-Track unavailable — falling back to CelesTrak for health detection (less reliable for BSTAR trends)');
    }
    if (healthData.length > 0) {
      try {
        const anomalies = await detectHealthAnomalies(supabase, healthData);
        if (anomalies.length > 0) {
          healthSignals = await createHealthSignals(supabase, anomalies);
          console.log(`[TLE] Health: ${anomalies.length} anomalies detected, ${healthSignals} new signals created`);
        } else {
          console.log('[TLE] Health: All satellites nominal');
        }
      } catch (healthError) {
        console.error('[TLE] Health detection error:', healthError);
      }
    }

    // Run maneuver detection on CelesTrak data (positional accuracy for maneuvers).
    // Uses 2σ outlier detection on mean motion deltas — same algorithm as client-side
    // lib/orbital/maneuver-detection.ts but persists to signals table.
    let maneuverSignals = 0;
    try {
      const maneuvers = await detectManeuvers(supabase);
      if (maneuvers.length > 0) {
        maneuverSignals = await createManeuverSignals(supabase, maneuvers);
        console.log(`[TLE] Maneuvers: ${maneuvers.length} detected, ${maneuverSignals} new signals created`);
      } else {
        console.log('[TLE] Maneuvers: No maneuvers detected in last 7 days');
      }
    } catch (maneuverError) {
      console.error('[TLE] Maneuver detection error:', maneuverError);
    }

    const totalDuration = Date.now() - startTime;

    const isPartial = !!(celestrakError || spacetrackError);

    return NextResponse.json({
      success: true,
      status: isPartial ? 'partial' : 'ok',
      celestrak: {
        status: celestrakError ? 'failed' : 'ok',
        satellites: celestrakData.length,
        newTLEs: celestrakNew,
        ...(celestrakError ? { reason: celestrakError } : {}),
      },
      spacetrack: {
        status: spacetrackError ? 'failed' : 'ok',
        satellites: spacetrackData.length,
        newTLEs: spacetrackNew,
        ...(spacetrackError ? { reason: spacetrackError } : {}),
      },
      health: {
        anomaliesDetected: healthData.length > 0 ? undefined : 'skipped',
        signalsCreated: healthSignals,
      },
      maneuvers: {
        signalsCreated: maneuverSignals,
      },
      totalSatellites: celestrakData.length + spacetrackData.length,
      totalNewTLEs: celestrakNew + spacetrackNew,
      duration: totalDuration,
      results,
      timestamp: new Date().toISOString(),
    });
  },
})

// Also support GET for manual testing
export const GET = POST
