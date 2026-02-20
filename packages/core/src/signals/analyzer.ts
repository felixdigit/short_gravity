/**
 * Signal Engine — Deterministic anomaly detection.
 *
 * Pure functions: z-score calculation, severity classification,
 * and anomaly detection against statistical baselines.
 *
 * No I/O. No database calls. Just math and rules.
 */

import {
  anomalyTypeEnum,
  severityEnum,
} from "@shortgravity/database";

// ─── Type Aliases (derived from DB enums) ───────────────────────────────────

export type AnomalyType = (typeof anomalyTypeEnum.enumValues)[number];
export type Severity = (typeof severityEnum.enumValues)[number];

// ─── Anomaly Configuration ──────────────────────────────────────────────────

/** Default z-score threshold per anomaly domain. */
export const ANOMALY_THRESHOLDS = {
  "ORB-DEV": 2.0,
  "ORB-MAN": 2.0,
  "REG-UNU": 2.0,
  "REG-UPD": 2.0,
  "MKT-VOL": 3.0,
  "MKT-PRC": 2.5,
  "MKT-OPT": 2.5,
  "NEWS-SPIKE": 3.0,
} as const satisfies Record<AnomalyType, number>;

/** Base severity for each anomaly type (before z-score escalation). */
const BASE_SEVERITY: Record<AnomalyType, Severity> = {
  "ORB-DEV": "medium",
  "ORB-MAN": "high",
  "REG-UNU": "medium",
  "REG-UPD": "high",
  "MKT-VOL": "medium",
  "MKT-PRC": "high",
  "MKT-OPT": "high",
  "NEWS-SPIKE": "medium",
};

/** Severity rank for escalation comparison. */
const SEVERITY_RANK: Record<Severity, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

const SEVERITY_BY_RANK: Severity[] = ["low", "medium", "high", "critical"];

// ─── Baseline Input ─────────────────────────────────────────────────────────

/** Minimal baseline shape needed for detection (avoids coupling to full Drizzle row). */
export interface BaselineInput {
  mean: number;
  stdDev: number;
  anomalyThresholdSigma?: number;
}

// ─── Detection Result ───────────────────────────────────────────────────────

export interface AnomalyDetectionResult {
  isAnomaly: boolean;
  zScore: number;
  severity: Severity;
  anomalyType: AnomalyType;
  observed: number;
  baselineMean: number;
  threshold: number;
}

// ─── Core Functions ─────────────────────────────────────────────────────────

/**
 * Calculate the z-score of an observed value against a baseline.
 *
 * z = (observed − mean) / stdDev
 *
 * Returns 0 when stdDev is 0 (no variance = no deviation).
 */
export function calculateZScore(
  observed: number,
  mean: number,
  stdDev: number,
): number {
  if (stdDev === 0) return 0;
  return (observed - mean) / stdDev;
}

/**
 * Determine severity for a given anomaly type and z-score.
 *
 * Rules:
 *   1. Start from the anomaly type's base severity.
 *   2. Escalate one level if |z| > 4σ.
 *   3. Escalate to critical if |z| > 6σ.
 *   4. Never exceed "critical".
 */
export function determineSeverity(
  anomalyType: AnomalyType,
  zScore: number,
): Severity {
  const absZ = Math.abs(zScore);
  let rank = SEVERITY_RANK[BASE_SEVERITY[anomalyType]];

  if (absZ > 6) {
    rank = SEVERITY_RANK.critical;
  } else if (absZ > 4) {
    rank = Math.min(rank + 1, SEVERITY_RANK.critical);
  }

  return SEVERITY_BY_RANK[rank];
}

/**
 * Run anomaly detection for a single observation against its baseline.
 *
 * Steps (from 01-SIGNAL-ENGINE.md):
 *   1. Calculate z-score: z = (observed − mean) / stdDev
 *   2. Check threshold: |z| > anomalyThresholdSigma → anomaly
 *   3. Classify severity
 */
export function detectAnomaly(
  observed: number,
  baseline: BaselineInput,
  anomalyType: AnomalyType,
): AnomalyDetectionResult {
  const zScore = calculateZScore(observed, baseline.mean, baseline.stdDev);

  const threshold =
    baseline.anomalyThresholdSigma ?? ANOMALY_THRESHOLDS[anomalyType];

  const isAnomaly = Math.abs(zScore) > threshold;
  const severity = isAnomaly
    ? determineSeverity(anomalyType, zScore)
    : "low";

  return {
    isAnomaly,
    zScore,
    severity,
    anomalyType,
    observed,
    baselineMean: baseline.mean,
    threshold,
  };
}

// ─── Baseline Calculation Utilities ─────────────────────────────────────────

/**
 * Calculate mean of a numeric series.
 */
export function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * Calculate population standard deviation.
 */
export function stdDev(values: number[]): number {
  if (values.length < 2) return 0;
  const avg = mean(values);
  const sumSquares = values.reduce((sum, v) => sum + (v - avg) ** 2, 0);
  return Math.sqrt(sumSquares / values.length);
}

/**
 * Calculate the median of a numeric series.
 */
export function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

/**
 * Calculate a percentile value from a sorted series.
 */
export function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(idx);
  const upper = Math.ceil(idx);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (idx - lower);
}

/**
 * Build a complete baseline from a series of metric values.
 */
export function buildBaseline(
  values: number[],
  thresholdSigma: number = 2.0,
): BaselineInput & { median: number; percentile95: number; sampleCount: number } {
  return {
    mean: mean(values),
    stdDev: stdDev(values),
    median: median(values),
    percentile95: percentile(values, 95),
    sampleCount: values.length,
    anomalyThresholdSigma: thresholdSigma,
  };
}

// ─── Signal Engine Configuration ────────────────────────────────────────────

export const SIGNAL_ENGINE_CONFIG = {
  polling: {
    regulatory: 15 * 60 * 1000,
    physical: 2 * 60 * 60 * 1000,
    market: 5 * 60 * 1000,
  },
  baselineWindows: {
    orbital: 30,
    filing: 90,
    market: 20,
    news: 14,
  },
  thresholds: {
    default: 2.0,
    orbital: 2.0,
    market: 2.5,
    news: 3.0,
  },
} as const;
