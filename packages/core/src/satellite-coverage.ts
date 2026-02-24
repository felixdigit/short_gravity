/**
 * Satellite Coverage Calculations
 *
 * Utilities for calculating satellite ground footprints, coverage cones,
 * and surface areas based on altitude and beam characteristics.
 */

const EARTH_RADIUS_KM = 6371; // Mean Earth radius in kilometers

/**
 * Coverage parameters for AST Spacemobile satellites
 * Based on publicly available information about their system
 */
export interface CoverageParams {
  /** Satellite altitude in kilometers */
  altitude: number;
  /** Minimum elevation angle from ground station (degrees) */
  minElevationAngle?: number;
  /** Beam half-angle for targeted coverage (degrees) - if known */
  beamHalfAngle?: number;
}

/**
 * Coverage cone geometry and metrics
 */
export interface CoverageGeometry {
  /** Half-angle of the coverage cone (degrees) */
  halfAngleDeg: number;
  /** Half-angle of the coverage cone (radians) */
  halfAngleRad: number;
  /** Radius of the ground footprint circle (km) */
  footprintRadiusKm: number;
  /** Surface area covered on Earth (km²) */
  surfaceAreaKm2: number;
  /** Diameter of coverage area (km) */
  diameterKm: number;
  /** Slant range from satellite to edge of footprint (km) */
  slantRangeKm: number;
}

/**
 * Calculate satellite coverage geometry
 *
 * Uses either:
 * 1. Specified beam half-angle (if known)
 * 2. Minimum elevation angle (typical for LEO satellites: 10-25°)
 * 3. Maximum geometric horizon (0° elevation) as fallback
 *
 * Reference: Satellite Communications by Dennis Roddy
 */
export function calculateCoverageGeometry(params: CoverageParams): CoverageGeometry {
  const { altitude, minElevationAngle = 10, beamHalfAngle } = params;

  let halfAngleDeg: number;
  let halfAngleRad: number;

  if (beamHalfAngle !== undefined) {
    // Use specified beam angle
    halfAngleDeg = beamHalfAngle;
    halfAngleRad = (beamHalfAngle * Math.PI) / 180;
  } else {
    // Calculate from minimum elevation angle
    // Using spherical Earth geometry
    const elevationRad = (minElevationAngle * Math.PI) / 180;
    const ratio = EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude);

    // Earth-central angle to coverage edge
    const earthCentralAngleRad = Math.acos(ratio * Math.cos(elevationRad)) - elevationRad;

    // Half-angle of coverage cone from satellite
    halfAngleRad = Math.asin(EARTH_RADIUS_KM * Math.sin(earthCentralAngleRad) / (EARTH_RADIUS_KM + altitude));
    halfAngleDeg = (halfAngleRad * 180) / Math.PI;
  }

  // Calculate footprint radius using spherical geometry
  // Earth-central angle from satellite nadir to coverage edge
  const earthCentralAngleRad = Math.asin(((EARTH_RADIUS_KM + altitude) / EARTH_RADIUS_KM) * Math.sin(halfAngleRad));

  // Arc length on Earth surface = footprint radius
  const footprintRadiusKm = EARTH_RADIUS_KM * earthCentralAngleRad;

  // Surface area of spherical cap
  // A = 2πRh where h = R(1 - cos(θ))
  const capHeight = EARTH_RADIUS_KM * (1 - Math.cos(earthCentralAngleRad));
  const surfaceAreaKm2 = 2 * Math.PI * EARTH_RADIUS_KM * capHeight;

  // Slant range from satellite to edge of footprint
  const slantRangeKm = Math.sqrt(
    altitude * altitude +
    2 * EARTH_RADIUS_KM * altitude +
    EARTH_RADIUS_KM * EARTH_RADIUS_KM * (1 - Math.cos(earthCentralAngleRad))
  );

  return {
    halfAngleDeg,
    halfAngleRad,
    footprintRadiusKm,
    surfaceAreaKm2,
    diameterKm: 2 * footprintRadiusKm,
    slantRangeKm,
  };
}

/**
 * Format surface area with appropriate units
 */
export function formatSurfaceArea(areaKm2: number): string {
  if (areaKm2 >= 1_000_000) {
    return `${(areaKm2 / 1_000_000).toFixed(2)} M km²`;
  } else if (areaKm2 >= 1_000) {
    return `${(areaKm2 / 1_000).toFixed(1)} K km²`;
  } else {
    return `${areaKm2.toFixed(0)} km²`;
  }
}

/**
 * AST Spacemobile specific coverage parameters
 *
 * Note: Exact beam specifications are proprietary, so we use
 * conservative estimates based on LEO satellite communications standards
 */
export const ASTS_COVERAGE_PARAMS = {
  /** Minimum elevation angle for reliable service (typical for LEO) */
  minElevationAngle: 15, // degrees

  /** Expected altitude range for ASTS constellation */
  altitudeRange: {
    min: 500, // km
    max: 550, // km
    nominal: 520, // km
  },
};

/**
 * Get coverage geometry for typical ASTS satellite
 */
export function getASTSCoverageGeometry(altitude: number): CoverageGeometry {
  return calculateCoverageGeometry({
    altitude,
    minElevationAngle: ASTS_COVERAGE_PARAMS.minElevationAngle,
  });
}

/**
 * Calculate coverage footprint radius (km) from satellite altitude
 *
 * This is the SINGLE SOURCE OF TRUTH for coverage radius calculation.
 * Uses spherical Earth geometry with minimum elevation angle.
 *
 * Formula: ρ = arccos(R·cos(ε) / (R+h)) - ε
 * Coverage radius = R × ρ (arc length on Earth surface)
 *
 * @param altitudeKm - Satellite altitude in kilometers
 * @param minElevationDeg - Minimum elevation angle in degrees (default: 20°)
 *                          AST uses 20° as practical cutoff for phased array gain
 * @returns Coverage radius in kilometers
 */
export function getCoverageRadiusKm(altitudeKm: number, minElevationDeg: number = 20): number {
  const R = EARTH_RADIUS_KM;
  const h = altitudeKm;

  // Convert minimum elevation angle to radians
  const minElevRad = minElevationDeg * Math.PI / 180;

  // Earth-centered angle to coverage edge
  // ρ = arccos(R·cos(ε) / (R+h)) - ε
  const rho = Math.acos((R * Math.cos(minElevRad)) / (R + h)) - minElevRad;

  // Ground distance (arc length)
  return R * rho;
}

/**
 * Calculate multiple coverage rings for different elevation angles
 * Useful for visualizing coverage quality zones
 */
export function calculateCoverageRings(altitude: number): {
  excellent: CoverageGeometry; // >25° elevation
  good: CoverageGeometry; // >15° elevation
  marginal: CoverageGeometry; // >10° elevation
  maximum: CoverageGeometry; // >0° elevation (horizon)
} {
  return {
    excellent: calculateCoverageGeometry({ altitude, minElevationAngle: 25 }),
    good: calculateCoverageGeometry({ altitude, minElevationAngle: 15 }),
    marginal: calculateCoverageGeometry({ altitude, minElevationAngle: 10 }),
    maximum: calculateCoverageGeometry({ altitude, minElevationAngle: 0 }),
  };
}
