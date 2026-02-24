import * as satellite from 'satellite.js'

/**
 * Propagate TLE to generate real orbital path
 * Uses satellite.js to calculate positions over one complete orbit
 */
export function propagateOrbitPath(
  tle1: string,
  tle2: string,
  numPoints: number = 120
): { lat: number; lon: number; alt: number }[] {
  const satrec = satellite.twoline2satrec(tle1, tle2)

  // Calculate orbital period from mean motion (revolutions per day)
  // Mean motion is in TLE line 2, positions 52-63
  const meanMotion = satrec.no // radians per minute
  const periodMinutes = (2 * Math.PI) / meanMotion // orbital period in minutes

  const points: { lat: number; lon: number; alt: number }[] = []
  const now = new Date()

  for (let i = 0; i < numPoints; i++) {
    // Distribute points evenly over one orbital period, centered on current time
    // Start from -half period (past) to +half period (future)
    const fraction = (i / numPoints) - 0.5  // -0.5 to +0.5
    const minutesOffset = fraction * periodMinutes
    const targetTime = new Date(now.getTime() + minutesOffset * 60 * 1000)

    const positionAndVelocity = satellite.propagate(satrec, targetTime)

    if (!positionAndVelocity || typeof positionAndVelocity.position === 'boolean') {
      continue
    }

    const positionEci = positionAndVelocity.position
    if (!positionEci || typeof positionEci === 'boolean') {
      continue
    }

    // Convert ECI to geodetic
    const gmst = satellite.gstime(targetTime)
    const positionGd = satellite.eciToGeodetic(positionEci, gmst)

    points.push({
      lat: satellite.degreesLat(positionGd.latitude),
      lon: satellite.degreesLong(positionGd.longitude),
      alt: positionGd.height
    })
  }

  return points
}
