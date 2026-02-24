/**
 * Hexasphere Grid Generator
 *
 * Generates a proper geodesic hexagonal grid using hexasphere.js.
 * This is the mathematically correct way to tessellate hexagons on a sphere.
 *
 * The algorithm:
 * 1. Start with icosahedron (20 triangular faces)
 * 2. Subdivide triangles recursively (numDivisions controls detail)
 * 3. Project vertices onto sphere surface
 * 4. Group triangles into hexagonal tiles (~12 pentagons at icosahedron vertices)
 */

import * as THREE from 'three';

// @ts-expect-error - hexasphere.js doesn't have type definitions
import Hexasphere from 'hexasphere.js';

interface HexaspherePoint {
  x: number;
  y: number;
  z: number;
}

interface HexasphereTile {
  centerPoint: HexaspherePoint;
  boundary: HexaspherePoint[];
}

export interface HexGridConfig {
  radius: number;       // Sphere radius (default 1 for unit sphere)
  numDivisions: number; // Subdivision level (higher = more detail, more tiles)
  tileWidth: number;    // Tile width factor (1.0 = touching tiles)
}

export const DEFAULT_HEXGRID_CONFIG: HexGridConfig = {
  radius: 1,
  numDivisions: 16,  // ~2562 tiles - good balance of detail and performance
  tileWidth: 1.0,
};

/**
 * Generate LineSegments geometry for hexasphere grid
 * Each edge is drawn exactly once (no duplicates)
 *
 * Memory-optimized: writes directly to pre-allocated Float32Array,
 * avoids intermediate edges array that caused allocation failures at high divisions.
 */
export function generateHexasphereGeometry(
  config: HexGridConfig = DEFAULT_HEXGRID_CONFIG,
  globeRadius: number = 1
): THREE.BufferGeometry {
  const hexasphere = new Hexasphere(config.radius, config.numDivisions, config.tileWidth);
  const tiles: HexasphereTile[] = hexasphere.tiles;

  // Pre-count boundary segments for upper-bound allocation
  let totalSegments = 0;
  for (const tile of tiles) totalSegments += tile.boundary.length;
  const maxEdges = Math.ceil(totalSegments / 2) + 100;

  // Pre-allocate — write positions directly as edges are discovered
  const positions = new Float32Array(maxEdges * 6);
  let edgeCount = 0;

  // Deduplicate edges via string keys
  const edgeSet = new Set<string>();
  const round = (n: number) => Math.round(n * 1000000) / 1000000;

  const makeEdgeKey = (p1: HexaspherePoint, p2: HexaspherePoint): string => {
    const k1 = `${round(p1.x)},${round(p1.y)},${round(p1.z)}`;
    const k2 = `${round(p2.x)},${round(p2.y)},${round(p2.z)}`;
    return k1 < k2 ? `${k1}|${k2}` : `${k2}|${k1}`;
  };

  for (const tile of tiles) {
    const boundary = tile.boundary;
    const numPoints = boundary.length;

    for (let i = 0; i < numPoints; i++) {
      const p1 = boundary[i];
      const p2 = boundary[(i + 1) % numPoints];

      const key = makeEdgeKey(p1, p2);
      if (!edgeSet.has(key)) {
        edgeSet.add(key);
        const idx = edgeCount * 6;
        positions[idx] = p1.x * globeRadius;
        positions[idx + 1] = p1.y * globeRadius;
        positions[idx + 2] = p1.z * globeRadius;
        positions[idx + 3] = p2.x * globeRadius;
        positions[idx + 4] = p2.y * globeRadius;
        positions[idx + 5] = p2.z * globeRadius;
        edgeCount++;
      }
    }
  }

  // Trim to actual size
  const trimmed = new Float32Array(positions.buffer, 0, edgeCount * 6);

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(trimmed, 3));

  return geometry;
}

/**
 * Get estimated tile count for a given subdivision level
 * Formula: 10 * 4^n + 2 where n = numDivisions
 * But hexasphere uses a different subdivision, roughly: 10 * n^2 + 2
 */
export function estimateTileCount(numDivisions: number): number {
  // Approximate formula for hexasphere.js
  return 10 * numDivisions * numDivisions + 2;
}

/**
 * Preset configurations for different detail levels
 */
export const HEXGRID_PRESETS = {
  // ~162 tiles - very coarse, good for testing
  LOW: { radius: 1, numDivisions: 4, tileWidth: 1.0 },

  // ~642 tiles - visible hex pattern
  MEDIUM: { radius: 1, numDivisions: 8, tileWidth: 1.0 },

  // ~2562 tiles - moderate detail
  HIGH: { radius: 1, numDivisions: 16, tileWidth: 1.0 },

  // ~10242 tiles - detailed
  ULTRA: { radius: 1, numDivisions: 32, tileWidth: 1.0 },

  // ~40962 tiles - AST reference density (matches their visualization)
  AST_DENSITY: { radius: 1, numDivisions: 64, tileWidth: 1.0 },
} as const;
