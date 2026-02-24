/**
 * @shortgravity/core — Domain logic entrypoint.
 *
 * Pure TypeScript business logic for Short Gravity.
 * No UI code. No API endpoints. No framework dependencies.
 */

// ─── Signals ────────────────────────────────────────────────────────────────

export {
  calculateZScore,
  determineSeverity,
  detectAnomaly,
  mean,
  stdDev,
  median,
  percentile,
  buildBaseline,
  ANOMALY_THRESHOLDS,
  SIGNAL_ENGINE_CONFIG,
} from "./signals/analyzer";

export type {
  AnomalyType,
  Severity,
  BaselineInput,
  AnomalyDetectionResult,
} from "./signals/analyzer";

export { generateMockSignals } from "./signals/mock";

// ─── Physics ────────────────────────────────────────────────────────────────

export {
  EARTH_RADIUS_KM,
  SCALE_FACTOR,
  DEG_TO_RAD,
  RAD_TO_DEG,
  GM_EARTH,
  EARTH_ROTATION_DEG_PER_SEC,
  SIDEREAL_DAY_S,
  LEO_MAX_ALT_KM,
  AST_NOMINAL_ALT_KM,
} from "./physics/constants";

export {
  calculateFootprintRadius,
  haversineDistance,
  isPointInCoverage,
  eciToScene,
} from "./physics/sgp4";

export type {
  EciVector,
  GeodeticPosition,
  SatellitePosition,
  TLEInput,
  CoverageParams,
  LOSResult,
  OrbitPathParams,
} from "./physics/sgp4";

// ─── Briefing ───────────────────────────────────────────────────────────────

export {
  buildFlashAlertPrompt,
  buildDeepAnalysisPrompt,
  buildStructuredAnalysisPrompt,
  buildScheduledReportPrompt,
} from "./briefing/generator";

export type {
  EntityProfile,
  SignalInput,
  SignalContextBundle,
  StructuredAnalysis,
  Implication,
  Confidence,
  BriefingType,
} from "./briefing/generator";

// ─── Satellite Coverage ──────────────────────────────────────────────────────

export {
  getCoverageRadiusKm,
  calculateCoverageGeometry,
  formatSurfaceArea,
  getASTSCoverageGeometry,
  calculateCoverageRings,
} from "./satellite-coverage";

export type {
  CoverageParams as SatelliteCoverageParams,
  CoverageGeometry,
} from "./satellite-coverage";

// ─── Orbital ─────────────────────────────────────────────────────────────────

export { propagateOrbitPath } from "./orbital";

// ─── Schemas ────────────────────────────────────────────────────────────────

export {
  // Enum schemas
  EntityTypeSchema,
  EntityStatusSchema,
  SeveritySchema,
  AnomalyTypeSchema,
  BriefingTypeSchema,
  TierSchema,
  BriefingStyleSchema,
  EmailDigestSchema,
  WatchlistPrioritySchema,
  ImplicationSchema,
  ConfidenceSchema,
  // Entity
  EntitySchema,
  // Signal
  SignalSchema,
  // Briefing
  BriefingSchema,
  GenerateBriefingRequestSchema,
  // Watchlist
  WatchlistItemSchema,
  AddToWatchlistRequestSchema,
  // Profile
  ProfileSchema,
  // Orbital
  EciVectorSchema,
  GeodeticSchema,
  SatellitePositionResponseSchema,
  ConstellationPositionsRequestSchema,
  OrbitPathRequestSchema,
  CoverageRequestSchema,
  CoverageResponseSchema,
  LOSRequestSchema,
  LOSResponseSchema,
  // Structured output
  StructuredAnalysisSchema,
  // Errors
  ErrorCodeSchema,
  ErrorResponseSchema,
  // Search
  SearchEntitiesRequestSchema,
  // Push
  RegisterPushTokenRequestSchema,
} from "./schemas";

export type {
  Entity,
  Signal,
  Briefing,
  GenerateBriefingRequest,
  WatchlistItem,
  AddToWatchlistRequest,
  Profile,
  SatellitePositionResponse,
  ConstellationPositionsRequest,
  OrbitPathRequest,
  CoverageRequest,
  CoverageResponse,
  LOSRequest,
  LOSResponse,
  StructuredAnalysisOutput,
  ErrorResponse,
  SearchEntitiesRequest,
  RegisterPushTokenRequest,
} from "./schemas";
