/**
 * Zod runtime validation schemas for Short Gravity API contracts.
 *
 * Derived from docs/architecture/05-API-CONTRACTS.md.
 * These schemas validate external input at system boundaries.
 */

import { z } from "zod";

// ─── Enum Schemas ───────────────────────────────────────────────────────────

export const EntityTypeSchema = z.enum([
  "satellite",
  "company",
  "constellation",
  "ground_station",
]);

export const EntityStatusSchema = z.enum([
  "active",
  "inactive",
  "decommissioned",
]);

export const SeveritySchema = z.enum(["low", "medium", "high", "critical"]);

export const AnomalyTypeSchema = z.enum([
  "ORB-DEV",
  "ORB-MAN",
  "REG-UNU",
  "REG-UPD",
  "MKT-VOL",
  "MKT-PRC",
  "MKT-OPT",
  "NEWS-SPIKE",
]);

export const BriefingTypeSchema = z.enum([
  "flash",
  "summary",
  "deep",
  "scheduled",
]);

export const TierSchema = z.enum(["free", "pro", "enterprise"]);

export const BriefingStyleSchema = z.enum([
  "technical",
  "executive",
  "balanced",
]);

export const EmailDigestSchema = z.enum(["none", "daily", "weekly"]);

export const WatchlistPrioritySchema = z.enum(["high", "medium", "low"]);

export const ImplicationSchema = z.enum([
  "bullish",
  "bearish",
  "neutral",
  "operational_concern",
]);

export const ConfidenceSchema = z.enum(["high", "medium", "low"]);

// ─── Entity Schemas ─────────────────────────────────────────────────────────

export const EntitySchema = z.object({
  id: z.string().uuid(),
  type: EntityTypeSchema,
  name: z.string(),
  slug: z.string(),
  description: z.string().nullable(),
  norad_id: z.string().nullable(),
  ticker: z.string().nullable(),
  status: EntityStatusSchema,
  metadata: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Entity = z.infer<typeof EntitySchema>;

// ─── Signal Schemas ─────────────────────────────────────────────────────────

export const SignalSchema = z.object({
  id: z.string(),
  anomaly_type: AnomalyTypeSchema,
  severity: SeveritySchema,
  entity_id: z.string().uuid(),
  entity_type: z.string(),
  entity_name: z.string(),
  metric_type: z.string(),
  observed_value: z.number().nullable(),
  baseline_value: z.number().nullable(),
  z_score: z.number().nullable(),
  raw_data: z.record(z.string(), z.unknown()),
  source: z.string(),
  processed: z.boolean(),
  briefing_id: z.string().uuid().nullable(),
  detected_at: z.string(),
  created_at: z.string(),
});

export type Signal = z.infer<typeof SignalSchema>;

// ─── Briefing Schemas ───────────────────────────────────────────────────────

export const BriefingSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  signal_id: z.string().uuid().nullable(),
  type: BriefingTypeSchema,
  title: z.string().nullable(),
  content: z.string(),
  model_used: z.string(),
  read: z.boolean(),
  created_at: z.string(),
});

export type Briefing = z.infer<typeof BriefingSchema>;

export const GenerateBriefingRequestSchema = z.object({
  signal_id: z.string().uuid(),
  briefing_type: z.enum(["flash", "summary", "deep"]),
});

export type GenerateBriefingRequest = z.infer<
  typeof GenerateBriefingRequestSchema
>;

// ─── Watchlist Schemas ──────────────────────────────────────────────────────

export const WatchlistItemSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  entity_id: z.string().uuid(),
  priority: WatchlistPrioritySchema,
  alert_on_severity: z.array(z.string()),
  notes: z.string().nullable(),
  created_at: z.string(),
});

export type WatchlistItem = z.infer<typeof WatchlistItemSchema>;

export const AddToWatchlistRequestSchema = z.object({
  entity_id: z.string().uuid(),
  priority: WatchlistPrioritySchema.optional().default("medium"),
  alert_on_severity: z
    .array(SeveritySchema)
    .optional()
    .default(["high", "critical"]),
});

export type AddToWatchlistRequest = z.infer<
  typeof AddToWatchlistRequestSchema
>;

// ─── Profile Schemas ────────────────────────────────────────────────────────

export const ProfileSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  full_name: z.string().nullable(),
  tier: TierSchema,
  briefing_style: BriefingStyleSchema,
  push_enabled: z.boolean(),
  email_digest: EmailDigestSchema,
});

export type Profile = z.infer<typeof ProfileSchema>;

// ─── Orbital Data Schemas ───────────────────────────────────────────────────

export const EciVectorSchema = z.object({
  x: z.number(),
  y: z.number(),
  z: z.number(),
});

export const GeodeticSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  altitude: z.number(),
});

export const SatellitePositionResponseSchema = z.object({
  satellite_id: z.string(),
  timestamp: z.string(),
  eci: EciVectorSchema,
  velocity: EciVectorSchema,
  geodetic: GeodeticSchema,
  tle_epoch: z.string(),
});

export type SatellitePositionResponse = z.infer<
  typeof SatellitePositionResponseSchema
>;

export const ConstellationPositionsRequestSchema = z.object({
  constellation_id: z.string().uuid().optional(),
  satellite_ids: z.array(z.string()).optional(),
  timestamp: z.string().optional(),
});

export type ConstellationPositionsRequest = z.infer<
  typeof ConstellationPositionsRequestSchema
>;

export const OrbitPathRequestSchema = z.object({
  satellite_id: z.string().uuid(),
  duration_minutes: z.number().positive().optional().default(90),
  steps: z.number().int().positive().optional().default(180),
});

export type OrbitPathRequest = z.infer<typeof OrbitPathRequestSchema>;

export const CoverageRequestSchema = z.object({
  satellite_id: z.string().uuid(),
  min_elevation_deg: z.number().min(0).max(90).optional().default(10),
  timestamp: z.string().optional(),
});

export type CoverageRequest = z.infer<typeof CoverageRequestSchema>;

export const CoverageResponseSchema = z.object({
  footprint_radius_km: z.number(),
  center: GeodeticSchema.pick({ latitude: true, longitude: true }),
  footprint_geojson: z.record(z.string(), z.unknown()),
});

export type CoverageResponse = z.infer<typeof CoverageResponseSchema>;

export const LOSRequestSchema = z.object({
  satellite_id: z.string().uuid(),
  ground_location: z.object({
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
    altitude_m: z.number().optional().default(0),
  }),
  timestamp: z.string().optional(),
});

export type LOSRequest = z.infer<typeof LOSRequestSchema>;

export const LOSResponseSchema = z.object({
  visible: z.boolean(),
  elevation_deg: z.number(),
  azimuth_deg: z.number(),
  range_km: z.number(),
  next_pass: z
    .object({
      aos: z.string(),
      los: z.string(),
      max_elevation_deg: z.number(),
    })
    .optional(),
});

export type LOSResponse = z.infer<typeof LOSResponseSchema>;

// ─── Structured Analysis Schema ─────────────────────────────────────────────

export const StructuredAnalysisSchema = z.object({
  situation: z.string(),
  analysis: z.object({
    technical: z.string(),
    historical: z.string(),
    crossDomain: z.string(),
  }),
  assessment: z.object({
    implication: ImplicationSchema,
    confidence: ConfidenceSchema,
    rationale: z.string(),
  }),
  watchItems: z.array(z.string()),
});

export type StructuredAnalysisOutput = z.infer<
  typeof StructuredAnalysisSchema
>;

// ─── Error Schema ───────────────────────────────────────────────────────────

export const ErrorCodeSchema = z.enum([
  "AUTH_REQUIRED",
  "FORBIDDEN",
  "NOT_FOUND",
  "VALIDATION_ERROR",
  "RATE_LIMITED",
]);

export const ErrorResponseSchema = z.object({
  error: z.object({
    code: ErrorCodeSchema,
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
  }),
});

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// ─── Search Schema ──────────────────────────────────────────────────────────

export const SearchEntitiesRequestSchema = z.object({
  query: z.string().min(1),
  types: z.array(EntityTypeSchema).optional(),
  limit: z.number().int().positive().max(100).optional().default(20),
});

export type SearchEntitiesRequest = z.infer<
  typeof SearchEntitiesRequestSchema
>;

// ─── Push Notification Schema ───────────────────────────────────────────────

export const RegisterPushTokenRequestSchema = z.object({
  token: z.string().min(1),
  platform: z.enum(["ios", "android"]),
});

export type RegisterPushTokenRequest = z.infer<
  typeof RegisterPushTokenRequestSchema
>;
