/**
 * Satellite color and styling system
 *
 * Each satellite gets a unique color for differentiation on the map.
 * Colors are chosen for visibility on dark backgrounds and to avoid
 * confusion with status colors (green/yellow/red).
 */

export interface SatelliteStyle {
  color: string        // Primary color (hex)
  colorDim: string     // Dimmed version for trails/orbits
  label: string        // Short label for legend
  shape: 'circle' | 'diamond' | 'square' | 'triangle'
}

// Monochrome white palette — SpaceX telemetry aesthetic
// All satellites use white at varying opacity tiers
const SATELLITE_COLORS = [
  '#FFFFFF', // White - BlueWalker 3
  '#FFFFFF', // White - BlueBird 1
  '#FFFFFF', // White - BlueBird 2
  '#FFFFFF', // White - BlueBird 3
  '#FFFFFF', // White - BlueBird 4
  '#FFFFFF', // White - BlueBird 5
  '#FFFFFF', // White - BlueBird 6
  '#FFFFFF', // White - Future satellites
  '#FFFFFF', // White
  '#FFFFFF', // White
]

// Map NORAD IDs to styles
// Short Gravity naming: BW3, BB1-BB5, FM1
const SATELLITE_STYLE_MAP: Record<string, SatelliteStyle> = {
  // BlueWalker 3 - The OG test satellite
  '53807': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'BW3',
    shape: 'diamond',
  },
  // BlueBird Block 1 (BB1-BB5)
  '61047': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'BB1',
    shape: 'circle',
  },
  '61048': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'BB2',
    shape: 'circle',
  },
  '61045': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'BB3',
    shape: 'circle',
  },
  '61049': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'BB4',
    shape: 'circle',
  },
  '61046': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'BB5',
    shape: 'circle',
  },
  // First Block 2 satellite (FM1)
  '67232': {
    color: '#FFFFFF',
    colorDim: 'rgba(255, 255, 255, 0.3)',
    label: 'FM1',
    shape: 'square',
  },
}

// Standard marker color (monochrome white)
export const SATELLITE_MARKER_COLOR = '#FFFFFF'
export const SATELLITE_MARKER_COLOR_DIM = 'rgba(255, 255, 255, 0.3)'

/**
 * Get short label for a satellite (BW3, BB1, FM1, etc.)
 */
export function getSatelliteLabel(noradId: string): string {
  return SATELLITE_STYLE_MAP[noradId]?.label || `S${noradId.slice(-2)}`
}

/**
 * Get style for a satellite by NORAD ID
 * Falls back to a generated style for unknown satellites
 */
export function getSatelliteStyle(noradId: string): SatelliteStyle {
  if (SATELLITE_STYLE_MAP[noradId]) {
    return SATELLITE_STYLE_MAP[noradId]
  }

  // Generate a consistent style for unknown satellites
  const hash = noradId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const colorIndex = hash % SATELLITE_COLORS.length
  const color = SATELLITE_COLORS[colorIndex]

  return {
    color,
    colorDim: color.replace('#', 'rgba(').replace(/(..)(..)(..)/, (_, r, g, b) =>
      `${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)}, 0.3)`
    ),
    label: `S${noradId.slice(-2)}`,
    shape: 'circle',
  }
}

/**
 * Get all known satellite styles (for legend)
 */
export function getAllSatelliteStyles(): { noradId: string; style: SatelliteStyle }[] {
  return Object.entries(SATELLITE_STYLE_MAP).map(([noradId, style]) => ({
    noradId,
    style,
  }))
}

/**
 * Convert hex color to THREE.js compatible format
 */
export function hexToThreeColor(hex: string): number {
  return parseInt(hex.replace('#', ''), 16)
}
