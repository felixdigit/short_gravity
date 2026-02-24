/**
 * BlueBird Satellite V3 Configuration
 *
 * Patent + CatSE-derived specifications for each generation
 * ControlSat: cylinder ~4.3m diameter, ~1.6m height (Block 2)
 * Array: flat tiles, 3-layer sandwich (solar/structural/antenna)
 */

export type BlueBirdGeneration = 'bluewalker3' | 'block1' | 'block2'

export interface GenerationConfig {
  // Array dimensions
  totalArrayArea: number        // m² - total phased array area
  arrayWidth: number            // m - total array width (tile columns × tile size)
  arrayLength: number           // m - total array length (tile rows × tile size)
  tilesPerRow: number           // number of tiles per row
  tilesPerCol: number           // number of tiles per column
  tileGap: number               // m - gap between tiles (nearly seamless)
  panelThickness: number        // m - thickness of tile

  // ControlSat (bus) dimensions — cylinder with flat sides
  busDiameter: number           // m - cylinder diameter
  busHeight: number             // m - cylinder height

  // Mass
  mass: number                  // kg
}

export const GENERATION_CONFIGS: Record<BlueBirdGeneration, GenerationConfig> = {
  bluewalker3: {
    totalArrayArea: 64,
    arrayWidth: 8,              // 8m total width
    arrayLength: 8,             // 8m total length
    tilesPerRow: 20,            // 20 tiles across
    tilesPerCol: 20,            // 20 tiles down
    tileGap: 0.005,             // ~5mm gap (tape spring width)
    panelThickness: 0.05,
    busDiameter: 2.5,           // Smaller prototype bus
    busHeight: 1.0,
    mass: 1500,
  },
  block1: {
    totalArrayArea: 64.38,
    arrayWidth: 8,
    arrayLength: 8,
    tilesPerRow: 20,
    tilesPerCol: 20,
    tileGap: 0.005,
    panelThickness: 0.05,
    busDiameter: 2.5,           // Similar to BW3
    busHeight: 1.0,
    mass: 1500,
  },
  block2: {
    totalArrayArea: 223,
    arrayWidth: 15,             // 15m total width
    arrayLength: 15,            // 15m total length
    tilesPerRow: 24,            // 24 tiles across
    tilesPerCol: 24,            // 24 tiles down
    tileGap: 0.005,
    panelThickness: 0.06,
    busDiameter: 4.3,           // CatSE: "4.3 m wide"
    busHeight: 1.6,             // CatSE: "1.6 m high"
    mass: 6100,
  },
}

// Colors — patent-accurate aluminum construction
export const COLORS = {
  // Tile/segment colors (brushed aluminum)
  segmentBase: '#B0B0B5',       // Brighter aluminum to catch reflections
  segmentCell: '#858588',       // Antenna pocket shadow (recessed)
  segmentEdge: '#787880',       // Tile edge color

  // Sandwich layer colors (visible at tile edges)
  honeycombCore: '#c8a850',     // Gold/amber honeycomb structural core
  solarCell: '#404555',         // Dark slate gray solar cell (matches official renders)
  tapeSpring: '#d0d0d2',       // Thin metal hinge strip between tiles

  // Bus colors
  busBody: '#1a1a1e',           // Near-black thermal blanket (MLI)
  busAccent: '#CCCCCC',         // Metallic trim
  busRing: '#3a3a3e',           // Zenith ring / stiffener

  // Frame (unused — kept for compat)
  frameColor: '#1f1f1f',
}

// Material properties — MeshPhysicalMaterial PBR
export const MATERIALS = {
  segment: {
    roughness: 0.35,
    metalness: 0.85,
    clearcoat: 0.3,
    clearcoatRoughness: 0.15,
    anisotropy: 0.6,
    anisotropyRotation: 0,
    ior: 2.5,
    envMapIntensity: 1.2,
    normalScale: 0.6,
  },
  tapeSpring: {
    roughness: 0.35,
    metalness: 0.85,
    clearcoat: 0.1,
    ior: 2.8,
  },
  bus: {
    roughness: 0.85,
    metalness: 0.15,
  },
  busRing: {
    roughness: 0.3,
    metalness: 0.9,
    clearcoat: 0.2,
    anisotropy: 0.3,
  },
  busAccent: {
    roughness: 0.3,
    metalness: 0.9,
    clearcoat: 0.2,
    anisotropy: 0.3,
  },
  honeycomb: {
    roughness: 0.6,
    metalness: 0.5,
    clearcoat: 0.1,
  },
  solarCell: {
    roughness: 0.4,
    metalness: 0.0,
    clearcoat: 0.4,
    ior: 1.5,
  },
}

// Utility functions
export function getTileSize(config: GenerationConfig): { w: number; h: number } {
  const totalGapsX = (config.tilesPerRow - 1) * config.tileGap
  const totalGapsZ = (config.tilesPerCol - 1) * config.tileGap
  return {
    w: (config.arrayWidth - totalGapsX) / config.tilesPerRow,
    h: (config.arrayLength - totalGapsZ) / config.tilesPerCol,
  }
}

export function getTotalArraySize(config: GenerationConfig): number {
  return Math.max(config.arrayWidth, config.arrayLength)
}

export function getSegmentCount(config: GenerationConfig): number {
  return config.tilesPerRow * config.tilesPerCol
}

// Legacy compat — maps to getTileSize
export function getSegmentSize(config: GenerationConfig): number {
  return getTileSize(config).w
}

// Map NORAD catalog IDs to satellite generation
export function getGenerationByNoradId(noradId: string): BlueBirdGeneration {
  const noradToGeneration: Record<string, BlueBirdGeneration> = {
    '53807': 'bluewalker3',
    '61047': 'block1',
    '61048': 'block1',
    '61045': 'block1',
    '61049': 'block1',
    '61046': 'block1',
    '67232': 'block2',
  }
  return noradToGeneration[noradId] || 'block1'
}
