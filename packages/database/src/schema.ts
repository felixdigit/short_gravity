/**
 * @shortgravity/database — Canonical Schema
 *
 * Domain: Orbital Intelligence (AST SpaceMobile)
 * ORM: Drizzle (PostgreSQL / Supabase)
 *
 * Tables derived from docs/architecture/04-DATA-MODEL.md
 * Enums derived from docs/architecture/01-SIGNAL-ENGINE.md
 */

import {
  pgTable,
  pgEnum,
  uuid,
  text,
  boolean,
  integer,
  bigint,
  decimal,
  date,
  timestamp,
  jsonb,
  uniqueIndex,
  index,
} from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";

// ─── Enums ──────────────────────────────────────────────────────────────────

export const entityTypeEnum = pgEnum("entity_type", [
  "satellite",
  "company",
  "constellation",
  "ground_station",
]);

export const entityStatusEnum = pgEnum("entity_status", [
  "active",
  "inactive",
  "decommissioned",
]);

export const orbitTypeEnum = pgEnum("orbit_type", [
  "LEO",
  "MEO",
  "GEO",
  "HEO",
  "SSO",
  "MOLNIYA",
]);

export const operationalStatusEnum = pgEnum("operational_status", [
  "operational",
  "partially_operational",
  "non_operational",
  "unknown",
  "decayed",
]);

export const severityEnum = pgEnum("severity", [
  "low",
  "medium",
  "high",
  "critical",
]);

export const anomalyTypeEnum = pgEnum("anomaly_type", [
  "ORB-DEV",
  "ORB-MAN",
  "REG-UNU",
  "REG-UPD",
  "MKT-VOL",
  "MKT-PRC",
  "MKT-OPT",
  "NEWS-SPIKE",
]);

export const tierEnum = pgEnum("tier", ["free", "pro", "enterprise"]);

export const briefingStyleEnum = pgEnum("briefing_style", [
  "technical",
  "executive",
  "balanced",
]);

export const emailDigestEnum = pgEnum("email_digest", [
  "none",
  "daily",
  "weekly",
]);

export const briefingTypeEnum = pgEnum("briefing_type", [
  "flash",
  "summary",
  "deep",
  "scheduled",
]);

export const watchlistPriorityEnum = pgEnum("watchlist_priority", [
  "high",
  "medium",
  "low",
]);

// ─── Tables ─────────────────────────────────────────────────────────────────

/** profiles — Extends Supabase auth.users */
export const profiles = pgTable(
  "profiles",
  {
    id: uuid("id").primaryKey(), // FK to auth.users, handled by Supabase trigger
    email: text("email").notNull(),
    fullName: text("full_name"),
    avatarUrl: text("avatar_url"),

    tier: tierEnum("tier").default("free").notNull(),
    tierExpiresAt: timestamp("tier_expires_at", { withTimezone: true }),

    briefingStyle: briefingStyleEnum("briefing_style").default("balanced"),
    pushEnabled: boolean("push_enabled").default(true),
    emailDigest: emailDigestEnum("email_digest").default("daily"),

    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
);

/** entities — Core entity registry */
export const entities = pgTable(
  "entities",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),
    type: entityTypeEnum("type").notNull(),
    name: text("name").notNull(),
    slug: text("slug").unique().notNull(),
    description: text("description"),

    noradId: text("norad_id"),
    ticker: text("ticker"),
    secCik: text("sec_cik"),

    status: entityStatusEnum("status").default("active"),

    metadata: jsonb("metadata").default({}),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_entities_type").on(t.type),
    index("idx_entities_slug").on(t.slug),
    index("idx_entities_norad_id").on(t.noradId),
    index("idx_entities_ticker").on(t.ticker),
  ],
);

/** satellites — Orbital body extension of entities */
export const satellites = pgTable(
  "satellites",
  {
    id: uuid("id")
      .primaryKey()
      .references(() => entities.id, { onDelete: "cascade" }),
    noradId: text("norad_id").unique().notNull(),

    constellationId: uuid("constellation_id").references(() => entities.id),
    operatorId: uuid("operator_id").references(() => entities.id),

    orbitType: orbitTypeEnum("orbit_type"),
    inclinationDeg: decimal("inclination_deg", { precision: 6, scale: 3 }),
    apogeeKm: decimal("apogee_km", { precision: 10, scale: 2 }),
    perigeeKm: decimal("perigee_km", { precision: 10, scale: 2 }),
    periodMin: decimal("period_min", { precision: 8, scale: 2 }),

    purpose: text("purpose"),
    launchDate: date("launch_date"),
    launchVehicle: text("launch_vehicle"),
    launchSite: text("launch_site"),

    tleLine1: text("tle_line1"),
    tleLine2: text("tle_line2"),
    tleEpoch: timestamp("tle_epoch", { withTimezone: true }),

    operationalStatus: operationalStatusEnum("operational_status").default(
      "unknown",
    ),

    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_satellites_constellation").on(t.constellationId),
    index("idx_satellites_operator").on(t.operatorId),
    index("idx_satellites_orbit_type").on(t.orbitType),
  ],
);

/** companies — Corporate entity extension */
export const companies = pgTable(
  "companies",
  {
    id: uuid("id")
      .primaryKey()
      .references(() => entities.id, { onDelete: "cascade" }),

    ticker: text("ticker"),
    exchange: text("exchange"),
    secCik: text("sec_cik"),

    sector: text("sector"),
    industry: text("industry"),
    foundedYear: integer("founded_year"),
    headquarters: text("headquarters"),
    website: text("website"),

    marketCap: bigint("market_cap", { mode: "number" }),
    employees: integer("employees"),

    satelliteCount: integer("satellite_count").default(0),
    constellationIds: uuid("constellation_ids")
      .array()
      .default(sql`'{}'`),

    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_companies_ticker").on(t.ticker),
    index("idx_companies_sector").on(t.sector),
  ],
);

/** briefings — AI-generated intelligence output */
export const briefings = pgTable(
  "briefings",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),

    userId: uuid("user_id")
      .notNull()
      .references(() => profiles.id),
    signalId: uuid("signal_id"), // FK added after signals table

    type: briefingTypeEnum("type").notNull(),
    title: text("title"),
    content: text("content").notNull(),
    structuredContent: jsonb("structured_content"),

    modelUsed: text("model_used").notNull(),
    tokensInput: integer("tokens_input"),
    tokensOutput: integer("tokens_output"),
    promptVersion: integer("prompt_version"),

    read: boolean("read").default(false),
    archived: boolean("archived").default(false),

    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_briefings_user").on(t.userId),
    index("idx_briefings_signal").on(t.signalId),
    index("idx_briefings_created_at").on(t.createdAt),
  ],
);

/** signals — Anomaly events detected by the Signal Engine */
export const signals = pgTable(
  "signals",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),

    anomalyType: anomalyTypeEnum("anomaly_type").notNull(),
    severity: severityEnum("severity").notNull(),

    entityId: uuid("entity_id")
      .notNull()
      .references(() => entities.id),
    entityType: text("entity_type").notNull(),
    entityName: text("entity_name").notNull(),

    metricType: text("metric_type").notNull(),
    observedValue: decimal("observed_value"),
    baselineValue: decimal("baseline_value"),
    zScore: decimal("z_score", { precision: 6, scale: 3 }),

    rawData: jsonb("raw_data").default({}),
    source: text("source").notNull(),

    relatedSignalIds: uuid("related_signal_ids")
      .array()
      .default(sql`'{}'`),

    processed: boolean("processed").default(false),
    briefingId: uuid("briefing_id").references(() => briefings.id),

    detectedAt: timestamp("detected_at", { withTimezone: true }).defaultNow(),
    eventTime: timestamp("event_time", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_signals_entity").on(t.entityId),
    index("idx_signals_severity").on(t.severity),
    index("idx_signals_type").on(t.anomalyType),
    index("idx_signals_detected_at").on(t.detectedAt),
  ],
);

/** baselines — Statistical baselines for anomaly detection */
export const baselines = pgTable(
  "baselines",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),

    entityId: uuid("entity_id")
      .notNull()
      .references(() => entities.id),
    metricType: text("metric_type").notNull(),

    mean: decimal("mean").notNull(),
    stdDev: decimal("std_dev").notNull(),
    median: decimal("median"),
    percentile95: decimal("percentile_95"),

    windowStart: timestamp("window_start", {
      withTimezone: true,
    }).notNull(),
    windowEnd: timestamp("window_end", { withTimezone: true }).notNull(),
    sampleCount: integer("sample_count").notNull(),

    anomalyThresholdSigma: decimal("anomaly_threshold_sigma").default("2.0"),

    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    uniqueIndex("idx_baselines_entity_metric").on(t.entityId, t.metricType),
  ],
);

/** watchlists — User → Entity subscription junction */
export const watchlists = pgTable(
  "watchlists",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),

    userId: uuid("user_id")
      .notNull()
      .references(() => profiles.id, { onDelete: "cascade" }),
    entityId: uuid("entity_id")
      .notNull()
      .references(() => entities.id, { onDelete: "cascade" }),

    priority: watchlistPriorityEnum("priority").default("medium"),

    alertOnSeverity: text("alert_on_severity")
      .array()
      .default(sql`'{high,critical}'`),
    alertTypes: text("alert_types").array(),

    customThresholds: jsonb("custom_thresholds").default({}),
    notes: text("notes"),

    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    uniqueIndex("idx_watchlists_user_entity").on(t.userId, t.entityId),
    index("idx_watchlists_user").on(t.userId),
    index("idx_watchlists_entity").on(t.entityId),
  ],
);

/** tle_history — Two-Line Element archive for orbital tracking */
export const tleHistory = pgTable(
  "tle_history",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),

    satelliteId: uuid("satellite_id")
      .notNull()
      .references(() => satellites.id),
    noradId: text("norad_id").notNull(),

    tleLine1: text("tle_line1").notNull(),
    tleLine2: text("tle_line2").notNull(),
    epoch: timestamp("epoch", { withTimezone: true }).notNull(),

    meanMotion: decimal("mean_motion", { precision: 12, scale: 8 }),
    eccentricity: decimal("eccentricity", { precision: 10, scale: 8 }),
    inclination: decimal("inclination", { precision: 8, scale: 4 }),

    source: text("source").default("space-track"),

    fetchedAt: timestamp("fetched_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_tle_history_satellite").on(t.satelliteId),
    index("idx_tle_history_epoch").on(t.epoch),
    index("idx_tle_history_norad_epoch").on(t.noradId, t.epoch),
  ],
);

/** metric_history — Time-series metrics for any entity */
export const metricHistory = pgTable(
  "metric_history",
  {
    id: uuid("id").primaryKey().default(sql`gen_random_uuid()`),

    entityId: uuid("entity_id")
      .notNull()
      .references(() => entities.id),
    metricType: text("metric_type").notNull(),
    value: decimal("value").notNull(),
    timestamp: timestamp("timestamp", { withTimezone: true }).notNull(),
    source: text("source").notNull(),
    metadata: jsonb("metadata").default({}),

    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow(),
  },
  (t) => [
    index("idx_metric_history_entity_type").on(t.entityId, t.metricType),
    index("idx_metric_history_timestamp").on(t.timestamp),
  ],
);
