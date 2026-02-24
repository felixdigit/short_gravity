'use client';

/**
 * CellGrid Component
 *
 * Renders a hexagonal cell grid on Earth's surface that is revealed
 * by satellite coverage footprints. Uses hexasphere.js for proper
 * geodesic tessellation - the mathematically correct way to tile
 * hexagons on a sphere.
 *
 * Based on FCC 23-65 filing: 48km diameter ground cells.
 */

import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import {
  generateHexasphereGeometry,
  HEXGRID_PRESETS,
} from '../../lib/hexasphere-grid';
import {
  coverageKmToRadians,
  latLonToNormalized3D,
} from './shaders/cellVisibility';

export interface SatellitePosition {
  lat: number;
  lon: number;
  altitudeKm: number;
  coverageRadiusKm: number;
}

interface CellGridProps {
  satellites: SatellitePosition[];
  globeRadius?: number;
  detailLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'ULTRA' | 'AST_DENSITY';
  cellColor?: string;
  opacity?: number;
  fadeEdge?: number;
  visible?: boolean;
}

// Line vertex shader - transforms position and passes to fragment
const lineVertexShader = /* glsl */ `
  varying vec3 vModelPosition;

  void main() {
    vModelPosition = position;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// Line fragment shader - checks coverage visibility
const lineFragmentShader = /* glsl */ `
  precision highp float;

  #define MAX_SATELLITES 20

  uniform vec3 uSatellitePositions[MAX_SATELLITES];
  uniform float uCoverageRadii[MAX_SATELLITES];
  uniform int uActiveSatellites;
  uniform vec3 uColor;
  uniform float uOpacity;
  uniform float uFadeEdge;

  varying vec3 vModelPosition;

  float sphericalAngle(vec3 p1, vec3 p2) {
    vec3 n1 = normalize(p1);
    vec3 n2 = normalize(p2);
    return acos(clamp(dot(n1, n2), -1.0, 1.0));
  }

  void main() {
    vec3 point = normalize(vModelPosition);
    float maxVisibility = 0.0;

    for (int i = 0; i < MAX_SATELLITES; i++) {
      if (i >= uActiveSatellites) break;

      vec3 satPoint = uSatellitePositions[i];
      float coverageAngle = uCoverageRadii[i];
      float angularDist = sphericalAngle(point, satPoint);

      if (angularDist <= coverageAngle) {
        float edgeStart = coverageAngle * (1.0 - uFadeEdge);
        if (angularDist <= edgeStart) {
          maxVisibility = 1.0;
          break;
        } else {
          float visibility = 1.0 - smoothstep(edgeStart, coverageAngle, angularDist);
          maxVisibility = max(maxVisibility, visibility);
        }
      }
    }

    if (maxVisibility < 0.01) {
      discard;
    }

    gl_FragColor = vec4(uColor, uOpacity * maxVisibility);
  }
`;

// Convert hex color to RGB array
function hexToRgb(hex: string): THREE.Color {
  return new THREE.Color(hex);
}

interface LineUniforms {
  [uniform: string]: { value: unknown };
  uSatellitePositions: { value: Float32Array };
  uCoverageRadii: { value: Float32Array };
  uActiveSatellites: { value: number };
  uColor: { value: THREE.Color };
  uOpacity: { value: number };
  uFadeEdge: { value: number };
}

function createLineUniforms(): LineUniforms {
  return {
    uSatellitePositions: { value: new Float32Array(60) },
    uCoverageRadii: { value: new Float32Array(20) },
    uActiveSatellites: { value: 0 },
    uColor: { value: new THREE.Color('#e98f50') },
    uOpacity: { value: 0.35 },
    uFadeEdge: { value: 0.2 },
  };
}

// Module-level geometry cache — survives re-renders and prop changes
const geometryCache = new Map<string, THREE.BufferGeometry>();

function getCachedGeometry(detailLevel: string, globeRadius: number): THREE.BufferGeometry {
  const key = `${detailLevel}_${globeRadius}`;
  let geo = geometryCache.get(key);
  if (!geo) {
    const preset = HEXGRID_PRESETS[detailLevel as keyof typeof HEXGRID_PRESETS];
    try {
      geo = generateHexasphereGeometry(preset, globeRadius);
    } catch {
      // Fallback to ULTRA if high-density preset exhausts memory
      const fallback = HEXGRID_PRESETS['ULTRA'];
      geo = generateHexasphereGeometry(fallback, globeRadius);
    }
    geometryCache.set(key, geo);
  }
  return geo;
}

export function CellGrid({
  satellites,
  globeRadius = 1,
  detailLevel = 'HIGH',
  cellColor = '#e98f50',
  opacity = 0.35,
  fadeEdge = 0.2,
  visible = true,
}: CellGridProps) {
  const linesRef = useRef<THREE.LineSegments>(null);
  const uniformsRef = useRef<LineUniforms>(createLineUniforms());

  // Geometry is cached at module level — instant on toggle
  const geometry = useMemo(() => {
    return getCachedGeometry(detailLevel, globeRadius);
  }, [detailLevel, globeRadius]);

  // Create shader material for lines
  const material = useMemo(() => {
    const uniforms = uniformsRef.current;
    uniforms.uColor.value = hexToRgb(cellColor);
    uniforms.uOpacity.value = opacity;
    uniforms.uFadeEdge.value = fadeEdge;

    return new THREE.ShaderMaterial({
      vertexShader: lineVertexShader,
      fragmentShader: lineFragmentShader,
      uniforms,
      transparent: true,
      depthWrite: false,
      depthTest: true,
    });
  }, [cellColor, opacity, fadeEdge]);

  // Update satellite positions in uniforms
  useEffect(() => {
    const uniforms = uniformsRef.current;
    const positions = uniforms.uSatellitePositions.value;
    const radii = uniforms.uCoverageRadii.value;

    positions.fill(0);
    radii.fill(0);

    const validSatellites = satellites.filter(sat =>
      sat.lat >= -90 && sat.lat <= 90 &&
      sat.lon >= -180 && sat.lon <= 180 &&
      sat.coverageRadiusKm > 0
    );

    const count = Math.min(validSatellites.length, 20);
    uniforms.uActiveSatellites.value = count;

    validSatellites.slice(0, 20).forEach((sat, i) => {
      const [x, y, z] = latLonToNormalized3D(sat.lat, sat.lon);
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      radii[i] = coverageKmToRadians(sat.coverageRadiusKm);
    });
  }, [satellites]);

  // Update uniforms each frame
  useFrame(() => {
    if (linesRef.current && material.uniforms) {
      material.uniformsNeedUpdate = true;
    }
  });

  return (
    <lineSegments ref={linesRef} geometry={geometry} material={material} renderOrder={1} visible={visible} />
  );
}
