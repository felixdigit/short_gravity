# Cockpit Architecture

**Component:** The Cockpit  
**Function:** Real-Time Asset Verification (Orbital Digital Twin)  
**Version:** 1.0

---

## Overview

The Cockpit is a 1:1 digital twin of the physical orbital environment. It renders live satellite positions and provides visual proof of asset location, coverage, and line-of-sight at any given moment.

---

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **Position Rendering** | Real-time 3D position of tracked satellites |
| **Coverage Visualization** | Ground footprint and field-of-view cones |
| **Line-of-Sight** | Visual proof of which ground stations can see which assets |
| **Conjunction Display** | Close approach warnings with trajectories |
| **Time Control** | Scrub forward/backward to verify past/future positions |

---

## Technical Architecture

### Orbital Mechanics Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COCKPIT RENDERING PIPELINE                       │
└─────────────────────────────────────────────────────────────────────────┘

     TLE Data              Propagation            Rendering
     ────────              ───────────            ─────────

┌──────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ Two-Line     │     │                   │     │                   │
│ Element Sets │────▶│   satellite.js    │────▶│  Three.js Scene   │
│ (from DB)    │     │   SGP4/SDP4       │     │  - Earth mesh     │
└──────────────┘     │   Propagator      │     │  - Satellite dots │
                     │                   │     │  - Orbit lines    │
                     └─────────┬─────────┘     │  - Coverage cones │
                               │               │                   │
                               ▼               └─────────┬─────────┘
                     ┌───────────────────┐               │
                     │ Position (ECI)    │               │
                     │ - x, y, z (km)    │               │
                     │ - vx, vy, vz      │               ▼
                     │ (km/s)            │     ┌───────────────────┐
                     └───────────────────┘     │  React Three      │
                               │               │  Fiber Component  │
                               ▼               │  Tree             │
                     ┌───────────────────┐     │                   │
                     │ Transform to      │────▶│  OrbitControls    │
                     │ Geodetic (LLA)    │     │  Camera           │
                     │ - lat, lon, alt   │     │  Lighting         │
                     └───────────────────┘     └───────────────────┘
```

### Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `satellite.js` | ^5.0.0 | SGP4/SDP4 propagation from TLE |
| `three` | ^0.160.0 | WebGL 3D rendering |
| `@react-three/fiber` | ^8.15.0 | React bindings for Three.js |
| `@react-three/drei` | ^9.90.0 | Useful helpers (OrbitControls, etc.) |

---

## Data Flow

### TLE to Position

```typescript
// lib/orbital/propagate.ts
import * as satellite from 'satellite.js';

export interface SatellitePosition {
  id: string;
  name: string;
  timestamp: Date;
  
  // Earth-Centered Inertial (km)
  eci: { x: number; y: number; z: number };
  velocity: { x: number; y: number; z: number };
  
  // Geodetic (for ground track)
  geodetic: {
    latitude: number;   // degrees
    longitude: number;  // degrees
    altitude: number;   // km
  };
}

export function propagateTLE(
  tleLine1: string,
  tleLine2: string,
  timestamp: Date
): SatellitePosition {
  // Parse TLE
  const satrec = satellite.twoline2satrec(tleLine1, tleLine2);
  
  // Propagate to timestamp
  const positionAndVelocity = satellite.propagate(satrec, timestamp);
  
  if (typeof positionAndVelocity.position === 'boolean') {
    throw new Error('Propagation failed');
  }
  
  const positionEci = positionAndVelocity.position;
  const velocityEci = positionAndVelocity.velocity as satellite.EciVec3<number>;
  
  // Convert to geodetic
  const gmst = satellite.gstime(timestamp);
  const positionGd = satellite.eciToGeodetic(positionEci, gmst);
  
  return {
    id: satrec.satnum,
    name: '', // populated from catalog
    timestamp,
    eci: positionEci,
    velocity: velocityEci,
    geodetic: {
      latitude: satellite.degreesLat(positionGd.latitude),
      longitude: satellite.degreesLong(positionGd.longitude),
      altitude: positionGd.height,
    },
  };
}
```

### Batch Propagation for Constellation

```typescript
// lib/orbital/constellation.ts
export function propagateConstellation(
  satellites: Array<{ id: string; name: string; tle1: string; tle2: string }>,
  timestamp: Date
): SatellitePosition[] {
  return satellites.map(sat => ({
    ...propagateTLE(sat.tle1, sat.tle2, timestamp),
    id: sat.id,
    name: sat.name,
  }));
}

// For animation: pre-compute positions at intervals
export function generateOrbitPath(
  tle1: string,
  tle2: string,
  startTime: Date,
  periodMinutes: number = 90,
  steps: number = 180
): SatellitePosition[] {
  const positions: SatellitePosition[] = [];
  const stepMs = (periodMinutes * 60 * 1000) / steps;
  
  for (let i = 0; i < steps; i++) {
    const t = new Date(startTime.getTime() + i * stepMs);
    positions.push(propagateTLE(tle1, tle2, t));
  }
  
  return positions;
}
```

---

## 3D Scene Structure

### React Three Fiber Component Tree

```
<Canvas>
  ├── <ambientLight />
  ├── <directionalLight />  (Sun position)
  ├── <OrbitControls />
  │
  ├── <Earth>
  │   ├── <mesh> (sphere geometry + texture)
  │   ├── <Atmosphere /> (glow shader)
  │   └── <Terminator /> (day/night line)
  │
  ├── <Satellites>
  │   └── {satellites.map(sat => (
  │       <SatelliteMarker key={sat.id} position={sat.eci} />
  │     ))}
  │
  ├── <OrbitPaths>
  │   └── {selectedSatellites.map(sat => (
  │       <OrbitLine key={sat.id} positions={sat.orbitPath} />
  │     ))}
  │
  ├── <CoverageCones>
  │   └── {showCoverage && selectedSatellites.map(sat => (
  │       <CoverageCone key={sat.id} satellite={sat} />
  │     ))}
  │
  └── <GroundStations>
      └── {groundStations.map(gs => (
          <GroundStationMarker key={gs.id} position={gs.geodetic} />
        ))}
</Canvas>
```

### Earth Component

```tsx
// components/cockpit/Earth.tsx
import { useTexture } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';

const EARTH_RADIUS_KM = 6371;
const SCALE_FACTOR = 1 / 1000; // 1 unit = 1000 km

export function Earth() {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const [dayMap, nightMap, normalMap, specularMap] = useTexture([
    '/textures/earth_day.jpg',
    '/textures/earth_night.jpg',
    '/textures/earth_normal.jpg',
    '/textures/earth_specular.jpg',
  ]);
  
  // Rotate Earth (optional, for realism)
  useFrame((state, delta) => {
    if (meshRef.current) {
      // Earth rotates 360° per 24 hours = 0.0042° per second
      meshRef.current.rotation.y += delta * 0.0042 * (Math.PI / 180);
    }
  });
  
  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[EARTH_RADIUS_KM * SCALE_FACTOR, 64, 64]} />
      <meshStandardMaterial
        map={dayMap}
        normalMap={normalMap}
        roughnessMap={specularMap}
      />
    </mesh>
  );
}
```

### Satellite Marker Component

```tsx
// components/cockpit/SatelliteMarker.tsx
import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef, useState } from 'react';
import * as THREE from 'three';

interface SatelliteMarkerProps {
  position: { x: number; y: number; z: number };
  name: string;
  selected: boolean;
  onClick: () => void;
  anomaly?: boolean;
}

const SCALE_FACTOR = 1 / 1000;

export function SatelliteMarker({ 
  position, 
  name, 
  selected,
  onClick,
  anomaly 
}: SatelliteMarkerProps) {
  const [hovered, setHovered] = useState(false);
  const meshRef = useRef<THREE.Mesh>(null);
  
  // Pulse animation for anomalies
  useFrame((state) => {
    if (meshRef.current && anomaly) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.3;
      meshRef.current.scale.setScalar(scale);
    }
  });
  
  // Convert km to scene units
  const pos: [number, number, number] = [
    position.x * SCALE_FACTOR,
    position.z * SCALE_FACTOR, // Three.js Y is up
    -position.y * SCALE_FACTOR,
  ];
  
  const color = anomaly ? '#ff4444' : selected ? '#00ff00' : '#ffffff';
  
  return (
    <group position={pos}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.02, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      
      {(hovered || selected) && (
        <Html distanceFactor={10}>
          <div className="bg-black/80 px-2 py-1 rounded text-white text-xs whitespace-nowrap">
            {name}
          </div>
        </Html>
      )}
    </group>
  );
}
```

---

## Coverage Calculation

### Field of View Cone

```typescript
// lib/orbital/coverage.ts

export interface CoverageParams {
  altitude: number;           // km
  minElevationAngle: number;  // degrees (typically 5-25°)
  beamWidth?: number;         // degrees (for spot beams)
}

export function calculateFootprintRadius(params: CoverageParams): number {
  const { altitude, minElevationAngle } = params;
  const EARTH_RADIUS = 6371;
  
  // Nadir angle from satellite's perspective
  const elevationRad = minElevationAngle * (Math.PI / 180);
  
  // Using spherical geometry
  const rho = Math.acos(
    (EARTH_RADIUS / (EARTH_RADIUS + altitude)) * Math.cos(elevationRad)
  ) - elevationRad;
  
  // Ground distance in km
  return EARTH_RADIUS * rho;
}

export function isPointInCoverage(
  satelliteGd: { latitude: number; longitude: number; altitude: number },
  groundPoint: { latitude: number; longitude: number },
  minElevation: number = 10
): boolean {
  const footprintRadius = calculateFootprintRadius({
    altitude: satelliteGd.altitude,
    minElevationAngle: minElevation,
  });
  
  // Haversine distance
  const distance = haversineDistance(
    satelliteGd.latitude,
    satelliteGd.longitude,
    groundPoint.latitude,
    groundPoint.longitude
  );
  
  return distance <= footprintRadius;
}
```

### Coverage Cone Visualization

```tsx
// components/cockpit/CoverageCone.tsx
import { useMemo } from 'react';
import * as THREE from 'three';
import { calculateFootprintRadius } from '@/lib/orbital/coverage';

interface CoverageConeProps {
  satellite: SatellitePosition;
  minElevation?: number;
  color?: string;
  opacity?: number;
}

export function CoverageCone({
  satellite,
  minElevation = 10,
  color = '#00ff00',
  opacity = 0.2,
}: CoverageConeProps) {
  const geometry = useMemo(() => {
    const footprint = calculateFootprintRadius({
      altitude: satellite.geodetic.altitude,
      minElevationAngle: minElevation,
    });
    
    // Create cone from satellite to Earth surface
    const height = satellite.geodetic.altitude * SCALE_FACTOR;
    const radius = footprint * SCALE_FACTOR;
    
    return new THREE.ConeGeometry(radius, height, 32, 1, true);
  }, [satellite, minElevation]);
  
  // Position cone at satellite, pointing toward Earth center
  const position = useMemo(() => {
    // ... transform to correct orientation
  }, [satellite]);
  
  return (
    <mesh geometry={geometry} position={position}>
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
```

---

## Line-of-Sight Calculation

```typescript
// lib/orbital/los.ts
import * as satellite from 'satellite.js';

export interface LOSResult {
  visible: boolean;
  elevation: number;  // degrees above horizon
  azimuth: number;    // degrees from north
  range: number;      // km
}

export function calculateLOS(
  satEci: satellite.EciVec3<number>,
  groundStation: { latitude: number; longitude: number; altitude: number },
  timestamp: Date
): LOSResult {
  const gmst = satellite.gstime(timestamp);
  
  // Ground station position
  const observerGd = {
    longitude: satellite.degreesToRadians(groundStation.longitude),
    latitude: satellite.degreesToRadians(groundStation.latitude),
    height: groundStation.altitude / 1000, // km
  };
  
  // Calculate look angles
  const positionEcf = satellite.eciToEcf(satEci, gmst);
  const lookAngles = satellite.ecfToLookAngles(observerGd, positionEcf);
  
  return {
    visible: lookAngles.elevation > 0,
    elevation: satellite.radiansToDegrees(lookAngles.elevation),
    azimuth: satellite.radiansToDegrees(lookAngles.azimuth),
    range: lookAngles.rangeSat,
  };
}
```

---

## Time Control

### Time Scrubbing Interface

```typescript
// hooks/useCockpitTime.ts
import { useState, useCallback, useEffect } from 'react';

export function useCockpitTime() {
  const [mode, setMode] = useState<'realtime' | 'historical' | 'future'>('realtime');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1x, 10x, 100x
  const [isPaused, setIsPaused] = useState(false);
  
  // Real-time tick
  useEffect(() => {
    if (mode !== 'realtime' || isPaused) return;
    
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => clearInterval(interval);
  }, [mode, isPaused]);
  
  // Playback tick (for historical/future)
  useEffect(() => {
    if (mode === 'realtime' || isPaused) return;
    
    const interval = setInterval(() => {
      setCurrentTime(prev => new Date(prev.getTime() + playbackSpeed * 1000));
    }, 1000);
    
    return () => clearInterval(interval);
  }, [mode, isPaused, playbackSpeed]);
  
  const jumpToTime = useCallback((time: Date) => {
    setCurrentTime(time);
    setMode(time > new Date() ? 'future' : 'historical');
  }, []);
  
  const goRealtime = useCallback(() => {
    setCurrentTime(new Date());
    setMode('realtime');
  }, []);
  
  return {
    currentTime,
    mode,
    playbackSpeed,
    isPaused,
    setPlaybackSpeed,
    setIsPaused,
    jumpToTime,
    goRealtime,
  };
}
```

---

## Performance Optimization

### Instanced Rendering for Large Constellations

```tsx
// components/cockpit/ConstellationInstanced.tsx
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ConstellationProps {
  positions: Array<{ x: number; y: number; z: number }>;
  colors: string[];
}

export function ConstellationInstanced({ positions, colors }: ConstellationProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const tempObject = useMemo(() => new THREE.Object3D(), []);
  const tempColor = useMemo(() => new THREE.Color(), []);
  
  // Update positions each frame
  useFrame(() => {
    if (!meshRef.current) return;
    
    positions.forEach((pos, i) => {
      tempObject.position.set(
        pos.x * SCALE_FACTOR,
        pos.z * SCALE_FACTOR,
        -pos.y * SCALE_FACTOR
      );
      tempObject.updateMatrix();
      meshRef.current!.setMatrixAt(i, tempObject.matrix);
      meshRef.current!.setColorAt(i, tempColor.set(colors[i]));
    });
    
    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  });
  
  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, positions.length]}>
      <sphereGeometry args={[0.015, 8, 8]} />
      <meshBasicMaterial />
    </instancedMesh>
  );
}
```

### Web Worker for Propagation

```typescript
// workers/propagation.worker.ts
import * as satellite from 'satellite.js';

self.onmessage = (e: MessageEvent) => {
  const { satellites, timestamp } = e.data;
  
  const positions = satellites.map((sat: any) => {
    const satrec = satellite.twoline2satrec(sat.tle1, sat.tle2);
    const pv = satellite.propagate(satrec, new Date(timestamp));
    
    if (typeof pv.position === 'boolean') return null;
    
    return {
      id: sat.id,
      eci: pv.position,
    };
  }).filter(Boolean);
  
  self.postMessage({ positions });
};
```

---

## File Structure

| File | Purpose |
|------|---------|
| `components/cockpit/CockpitCanvas.tsx` | Main 3D canvas container |
| `components/cockpit/Earth.tsx` | Earth mesh with textures |
| `components/cockpit/SatelliteMarker.tsx` | Individual satellite dot |
| `components/cockpit/ConstellationInstanced.tsx` | Instanced rendering for scale |
| `components/cockpit/OrbitLine.tsx` | Orbit path polyline |
| `components/cockpit/CoverageCone.tsx` | Ground coverage visualization |
| `components/cockpit/TimeControls.tsx` | Playback UI |
| `lib/orbital/propagate.ts` | TLE propagation utilities |
| `lib/orbital/coverage.ts` | Footprint calculations |
| `lib/orbital/los.ts` | Line-of-sight math |
| `hooks/useCockpitTime.ts` | Time control state |
| `workers/propagation.worker.ts` | Offload propagation to worker |

---

## Texture Assets Required

| Asset | Source | Resolution |
|-------|--------|------------|
| `earth_day.jpg` | NASA Blue Marble | 8192x4096 |
| `earth_night.jpg` | NASA Black Marble | 8192x4096 |
| `earth_normal.jpg` | Generated normal map | 4096x2048 |
| `earth_specular.jpg` | Ocean specular mask | 4096x2048 |
| `starfield.jpg` | Deep sky background | 4096x2048 |

Store in `/public/textures/`. Compress to WebP for production.

---

## Mobile Optimization (iOS)

- Use lower-resolution textures (2048x1024)
- Reduce sphere segment count (32 vs 64)
- Limit visible satellites (show top 50 by relevance)
- Disable shadows
- Use `frameloop="demand"` to render only on interaction
