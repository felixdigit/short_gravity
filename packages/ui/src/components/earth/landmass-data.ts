/**
 * Earth landmass data for visualization
 *
 * Points are generated using Fibonacci sphere distribution filtered
 * against a NASA land mask image (SpaceX-style approach).
 */

// Import auto-generated landmass points from JSON (smaller bundle size)
import landmassPointsData from './landmass-points.json'

export interface LandmassPoint {
  lat: number
  lon: number
}

export const LANDMASS_POINTS: LandmassPoint[] = landmassPointsData as LandmassPoint[]

// Simplified coastline segments for outline rendering (optional enhancement)
// Each segment is a connected line of lat/lon points
export const COASTLINE_SEGMENTS: [number, number][][] = [
  // Americas West Coast
  [[60, -145], [55, -135], [50, -125], [45, -124], [40, -124], [35, -120], [30, -117], [25, -110]],
  // Americas East Coast
  [[45, -65], [42, -70], [38, -75], [35, -76], [30, -80], [25, -80], [20, -87]],
  // Europe West
  [[60, -5], [55, -5], [50, -5], [48, -5], [44, -8], [43, -9], [37, -9], [36, -6]],
  // Africa West
  [[35, -6], [30, -10], [25, -15], [15, -17], [10, -15], [5, -5], [0, 5], [-5, 10]],
  // Africa East
  [[30, 32], [25, 35], [15, 40], [10, 45], [0, 43], [-5, 40], [-15, 35], [-25, 33]],
  // Australia
  [[-12, 130], [-15, 125], [-20, 118], [-25, 114], [-32, 115], [-35, 118], [-37, 140], [-38, 145]],
  // East Asia
  [[55, 140], [50, 140], [45, 135], [40, 124], [35, 126], [30, 122], [25, 120], [20, 110]],
]

/**
 * Generate orbit path points that passes through a satellite's current position
 * Used for visualizing satellite orbital ground tracks
 *
 * @param inclination - Orbital inclination in degrees
 * @param currentLat - Satellite's current latitude in degrees
 * @param currentLon - Satellite's current longitude in degrees
 * @param numPoints - Number of points to generate along the orbit
 * @returns Array of [lat, lon] coordinate pairs
 */
export function generateOrbitPath(
  inclination: number,
  currentLat: number = 0,
  currentLon: number = 0,
  numPoints: number = 72
): [number, number][] {
  const points: [number, number][] = []
  const incRad = (inclination * Math.PI) / 180
  const currentLatRad = (currentLat * Math.PI) / 180
  const currentLonRad = (currentLon * Math.PI) / 180

  // Calculate the argument of latitude (angle along orbit from ascending node)
  // from the satellite's current position
  // For an inclined orbit: sin(lat) = sin(inc) * sin(argLat)
  // So: argLat = asin(sin(lat) / sin(inc))
  let argLatRad = 0
  if (Math.abs(inclination) > 0.1) {
    const sinArgLat = Math.sin(currentLatRad) / Math.sin(incRad)
    // Clamp to valid range for asin
    const clampedSin = Math.max(-1, Math.min(1, sinArgLat))
    argLatRad = Math.asin(clampedSin)

    // Determine if we're in the ascending or descending part of the orbit
    // by checking if we're moving north (ascending) or south (descending)
    // For simplicity, use longitude difference from RAAN to determine quadrant
  }

  // Calculate RAAN from current position and argument of latitude
  // lon = atan2(cos(inc) * sin(argLat), cos(argLat)) + raan
  // So: raan = lon - atan2(cos(inc) * sin(argLat), cos(argLat))
  const raanRad = currentLonRad - Math.atan2(
    Math.cos(incRad) * Math.sin(argLatRad),
    Math.cos(argLatRad)
  )

  for (let i = 0; i <= numPoints; i++) {
    // Start from current position and go around the orbit
    const angle = argLatRad + (i / numPoints) * 2 * Math.PI

    // Calculate position on inclined orbit
    const x = Math.cos(angle)
    const y = Math.sin(angle) * Math.cos(incRad)
    const z = Math.sin(angle) * Math.sin(incRad)

    // Apply RAAN rotation
    const xRot = x * Math.cos(raanRad) - y * Math.sin(raanRad)
    const yRot = x * Math.sin(raanRad) + y * Math.cos(raanRad)

    // Convert to lat/lon
    const lat = Math.asin(z) * (180 / Math.PI)
    const lon = Math.atan2(yRot, xRot) * (180 / Math.PI)

    points.push([lat, lon])
  }

  return points
}
