/**
 * SGP4 propagation interfaces & pure geometry functions.
 *
 * These types define the contract between TLE data in the database
 * and the rendering/analysis layers. The actual satellite.js calls
 * live in the frontend or edge functions — this module is pure math.
 */

import { EARTH_RADIUS_KM, DEG_TO_RAD } from "./constants";

// ─── Core Interfaces ────────────────────────────────────────────────────────

/** Earth-Centered Inertial vector (km or km/s). */
export interface EciVector {
  x: number;
  y: number;
  z: number;
}

/** Geodetic coordinates (degrees + km altitude). */
export interface GeodeticPosition {
  latitude: number;
  longitude: number;
  altitude: number;
}

/** Full satellite state at a moment in time. */
export interface SatellitePosition {
  id: string;
  name: string;
  timestamp: Date;
  eci: EciVector;
  velocity: EciVector;
  geodetic: GeodeticPosition;
}

/** TLE input for propagation. */
export interface TLEInput {
  id: string;
  name: string;
  tle1: string;
  tle2: string;
}

/** Parameters for coverage footprint calculation. */
export interface CoverageParams {
  altitude: number;
  minElevationAngle: number;
  beamWidth?: number;
}

/** Line-of-sight result from a ground observer to a satellite. */
export interface LOSResult {
  visible: boolean;
  elevation: number;
  azimuth: number;
  range: number;
}

/** Orbit path generation parameters. */
export interface OrbitPathParams {
  tle1: string;
  tle2: string;
  startTime: Date;
  periodMinutes?: number;
  steps?: number;
}

// ─── Pure Geometry Functions ────────────────────────────────────────────────

/**
 * Calculate the ground footprint radius of a satellite's coverage cone.
 *
 * Uses spherical geometry:
 *   ρ = acos( R / (R + h) · cos(ε) ) − ε
 *   footprint = R · ρ
 *
 * where R = Earth radius, h = altitude, ε = min elevation angle.
 */
export function calculateFootprintRadius(params: CoverageParams): number {
  const { altitude, minElevationAngle } = params;
  const elevationRad = minElevationAngle * DEG_TO_RAD;

  const rho =
    Math.acos(
      (EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude)) *
        Math.cos(elevationRad),
    ) - elevationRad;

  return EARTH_RADIUS_KM * rho;
}

/**
 * Haversine great-circle distance between two geodetic points (km).
 */
export function haversineDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const dLat = (lat2 - lat1) * DEG_TO_RAD;
  const dLon = (lon2 - lon1) * DEG_TO_RAD;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * DEG_TO_RAD) *
      Math.cos(lat2 * DEG_TO_RAD) *
      Math.sin(dLon / 2) ** 2;

  return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Check whether a ground point falls within a satellite's coverage cone.
 */
export function isPointInCoverage(
  satelliteGd: GeodeticPosition,
  groundPoint: { latitude: number; longitude: number },
  minElevation: number = 10,
): boolean {
  const footprintRadius = calculateFootprintRadius({
    altitude: satelliteGd.altitude,
    minElevationAngle: minElevation,
  });

  const distance = haversineDistance(
    satelliteGd.latitude,
    satelliteGd.longitude,
    groundPoint.latitude,
    groundPoint.longitude,
  );

  return distance <= footprintRadius;
}

/**
 * Convert ECI coordinates to scene-space (Three.js Y-up) at a given scale.
 */
export function eciToScene(
  eci: EciVector,
  scaleFactor: number,
): [x: number, y: number, z: number] {
  return [
    eci.x * scaleFactor,
    eci.z * scaleFactor,
    -eci.y * scaleFactor,
  ];
}
