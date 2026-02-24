'use client'

import { useRef, useMemo, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import * as THREE from 'three'
import { LANDMASS_POINTS } from './landmass-data'
import { SATELLITE_MARKER_COLOR } from './satellite-colors'

// Surgical accent — orange for satellite markers, coverage, hex grid
const SELECTION_COLOR = '#FF6B35'
import { getGenerationByNoradId, GENERATION_CONFIGS, COLORS as SAT_COLORS, type BlueBirdGeneration } from './satellite/config'
import { CellGrid, type SatellitePosition } from './CellGrid'

export interface SatelliteData {
  noradId: string
  name: string
  latitude: number
  longitude: number
  altitude: number
  inclination?: number  // degrees - from Space-Track INCLINATION
  raan?: number         // degrees - from Space-Track RA_OF_ASC_NODE
  tle?: {               // Raw TLE lines for real orbit propagation
    line1: string
    line2: string
  }
}

interface Globe3DProps {
  satellites?: SatelliteData[]
  selectedSatellite?: string
  onSelectSatellite?: (noradId: string | undefined) => void
  autoRotate?: boolean
  showOrbits?: boolean
  showCoverage?: boolean  // Show coverage footprint circles (legacy)
  showCellGrid?: boolean  // Show fixed cell grid revealed by satellite footprints
  className?: string
  useDotMarkers?: boolean  // Use simple orange dots instead of 3D models
  paused?: boolean  // Pause render loop (portal open)
  coverageRadii?: Record<string, number>  // Pre-computed: noradId → coverage radius km
  orbitPaths?: Record<string, { lat: number; lon: number; alt: number }[]>  // Pre-computed orbit paths
}

const EARTH_RADIUS_KM = 6371

// Convert lat/lon/alt to 3D coordinates
function latLonToVector3(lat: number, lon: number, radius: number = 1): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)

  const x = -radius * Math.sin(phi) * Math.cos(theta)
  const y = radius * Math.cos(phi)
  const z = radius * Math.sin(phi) * Math.sin(theta)

  return new THREE.Vector3(x, y, z)
}

// Solid Earth sphere - provides depth occlusion for orbits behind globe
// Also handles click-to-deselect when clicking on empty space
function WireframeEarth() {
  return (
    <mesh>
      <sphereGeometry args={[0.998, 64, 32]} />
      <meshBasicMaterial
        color="#0a0f14"
        depthWrite={true}
      />
    </mesh>
  )
}

// Shader for grid lines with camera-aware fading
const gridVertexShader = `
  uniform vec3 uCameraPosition;
  varying float vVisibility;

  void main() {
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vec3 viewDir = normalize(uCameraPosition - worldPosition.xyz);
    vec3 normal = normalize(worldPosition.xyz);
    float dotProduct = dot(normal, viewDir);
    vVisibility = smoothstep(-0.1, 0.5, dotProduct);

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    gl_PointSize = 3.0 * (1.0 / -mvPosition.z);
  }
`

const gridFragmentShader = `
  uniform float uBaseOpacity;
  varying float vVisibility;

  void main() {
    vec2 center = gl_PointCoord - 0.5;
    float dist = length(center);
    if (dist > 0.5) discard;

    float alpha = uBaseOpacity * vVisibility;
    gl_FragColor = vec4(1.0, 1.0, 1.0, alpha);
  }
`

// Grid lines (latitude/longitude) - subtle, with camera-aware fading
function GridLines() {
  const { camera } = useThree()
  const materialRef = useRef<THREE.ShaderMaterial>(null)

  const positions = useMemo(() => {
    const points: THREE.Vector3[] = []

    // Equator (slightly more visible)
    for (let lon = 0; lon <= 360; lon += 3) {
      points.push(latLonToVector3(0, lon, 1.002))
    }

    // Latitude lines (every 30 degrees, subtle)
    for (let lat = -60; lat <= 60; lat += 30) {
      if (lat === 0) continue
      for (let lon = 0; lon <= 360; lon += 6) {
        points.push(latLonToVector3(lat, lon, 1.001))
      }
    }

    // Longitude lines (every 30 degrees)
    for (let lon = 0; lon < 360; lon += 30) {
      for (let lat = -90; lat <= 90; lat += 6) {
        points.push(latLonToVector3(lat, lon, 1.001))
      }
    }

    return new Float32Array(points.flatMap(v => [v.x, v.y, v.z]))
  }, [])

  useFrame(() => {
    if (materialRef.current) {
      materialRef.current.uniforms.uCameraPosition.value.copy(camera.position)
    }
  })

  const shaderMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uCameraPosition: { value: new THREE.Vector3() },
        uBaseOpacity: { value: 0.15 }
      },
      vertexShader: gridVertexShader,
      fragmentShader: gridFragmentShader,
      transparent: true,
      depthWrite: false
    })
  }, [])

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={positions.length / 3}
          itemSize={3}
        />
      </bufferGeometry>
      <primitive object={shaderMaterial} ref={materialRef} attach="material" />
    </points>
  )
}

// Custom shader material for camera-aware point fading
// Points facing the camera are fully visible, back-facing points fade out
const landmassVertexShader = `
  uniform vec3 uCameraPosition;
  varying float vVisibility;

  void main() {
    // Transform position to world space
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);

    // Calculate view direction from point to camera
    vec3 viewDir = normalize(uCameraPosition - worldPosition.xyz);

    // Normal for a sphere point is just its normalized position
    vec3 normal = normalize(worldPosition.xyz);

    // Dot product: 1 = facing camera, -1 = facing away
    float dotProduct = dot(normal, viewDir);

    // Remap: back-facing (< 0) = 0, front-facing (> 0) = gradual fade
    // Using smoothstep for a gradual transition at the edges
    vVisibility = smoothstep(-0.1, 0.5, dotProduct);

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    // Size attenuation (like sizeAttenuation: true)
    gl_PointSize = 10.0 * (1.0 / -mvPosition.z);
  }
`

const landmassFragmentShader = `
  uniform float uBaseOpacity;
  uniform vec3 uColor;
  varying float vVisibility;

  void main() {
    // Circular point shape
    vec2 center = gl_PointCoord - 0.5;
    float dist = length(center);
    if (dist > 0.5) discard;

    // Apply visibility fade based on camera angle
    float alpha = uBaseOpacity * vVisibility;

    gl_FragColor = vec4(uColor, alpha);
  }
`

// Dot-density landmass visualization with camera-aware fading
function Landmasses() {
  const { camera } = useThree()
  const materialRef = useRef<THREE.ShaderMaterial>(null)

  const positions = useMemo(() => {
    const points = LANDMASS_POINTS.map(({ lat, lon }) =>
      latLonToVector3(lat, lon, 1.003)
    )
    return new Float32Array(points.flatMap(v => [v.x, v.y, v.z]))
  }, [])

  // Update camera position uniform each frame
  useFrame(() => {
    if (materialRef.current) {
      materialRef.current.uniforms.uCameraPosition.value.copy(camera.position)
    }
  })

  const shaderMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uCameraPosition: { value: new THREE.Vector3() },
        uBaseOpacity: { value: 0.7 },
        uColor: { value: new THREE.Color('#a1a1aa') }  // Muted gray - zinc-400
      },
      vertexShader: landmassVertexShader,
      fragmentShader: landmassFragmentShader,
      transparent: true,
      depthWrite: false
    })
  }, [])

  return (
    <points>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          array={positions}
          count={positions.length / 3}
          itemSize={3}
        />
      </bufferGeometry>
      <primitive object={shaderMaterial} ref={materialRef} attach="material" />
    </points>
  )
}

// Coverage footprint cone visualization
// Projects from satellite to Earth surface showing coverage area
function CoverageFootprint({
  satellite,
  isSelected,
  color,
  coverageRadiusKm
}: {
  satellite: SatelliteData
  isSelected: boolean
  color: string
  coverageRadiusKm: number
}) {
  const footprint = useMemo(() => {
    // Calculate the angular radius of the coverage circle on Earth's surface
    // Using spherical geometry: angular_radius = coverage_radius / earth_radius (in radians)
    const angularRadiusRad = coverageRadiusKm / EARTH_RADIUS_KM

    // Get satellite position on normalized globe (radius 1)
    const satLat = satellite.latitude
    const satLon = satellite.longitude

    // Generate circle points on Earth's surface
    const numPoints = 64
    const circlePoints: THREE.Vector3[] = []

    for (let i = 0; i <= numPoints; i++) {
      const angle = (i / numPoints) * 2 * Math.PI

      // Calculate point on coverage circle using spherical coordinates
      // This accounts for the curvature of the Earth
      const lat = Math.asin(
        Math.sin(satLat * Math.PI / 180) * Math.cos(angularRadiusRad) +
        Math.cos(satLat * Math.PI / 180) * Math.sin(angularRadiusRad) * Math.cos(angle)
      ) * 180 / Math.PI

      const lon = satLon + Math.atan2(
        Math.sin(angle) * Math.sin(angularRadiusRad) * Math.cos(satLat * Math.PI / 180),
        Math.cos(angularRadiusRad) - Math.sin(satLat * Math.PI / 180) * Math.sin(lat * Math.PI / 180)
      ) * 180 / Math.PI

      // Slightly above Earth surface for visibility (increased offset to avoid z-fighting)
      circlePoints.push(latLonToVector3(lat, lon, 1.006))
    }

    // Create the coverage circle outline
    const geo = new THREE.BufferGeometry()
    const positions = new Float32Array(circlePoints.flatMap(v => [v.x, v.y, v.z]))
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const mat = new THREE.LineBasicMaterial({
      color,
      opacity: isSelected ? 0.9 : 0.6,
      transparent: true,
      linewidth: 2,
      depthWrite: false
    })

    return new THREE.LineLoop(geo, mat)
  }, [satellite.noradId, satellite.latitude, satellite.longitude, satellite.altitude, color, isSelected])

  // Create filled coverage area (semi-transparent)
  const filledArea = useMemo(() => {
    const angularRadiusRad = coverageRadiusKm / EARTH_RADIUS_KM

    const satLat = satellite.latitude
    const satLon = satellite.longitude

    // Create a circular mesh on Earth's surface
    const numSegments = 32
    const vertices: number[] = []
    const indices: number[] = []

    // Center point (increased offset to avoid z-fighting with Earth sphere)
    const center = latLonToVector3(satLat, satLon, 1.005)
    vertices.push(center.x, center.y, center.z)

    // Circle points (don't include closing point - we close with indices)
    for (let i = 0; i < numSegments; i++) {
      const angle = (i / numSegments) * 2 * Math.PI

      const lat = Math.asin(
        Math.sin(satLat * Math.PI / 180) * Math.cos(angularRadiusRad) +
        Math.cos(satLat * Math.PI / 180) * Math.sin(angularRadiusRad) * Math.cos(angle)
      ) * 180 / Math.PI

      const lon = satLon + Math.atan2(
        Math.sin(angle) * Math.sin(angularRadiusRad) * Math.cos(satLat * Math.PI / 180),
        Math.cos(angularRadiusRad) - Math.sin(satLat * Math.PI / 180) * Math.sin(lat * Math.PI / 180)
      ) * 180 / Math.PI

      const point = latLonToVector3(lat, lon, 1.005)
      vertices.push(point.x, point.y, point.z)
    }

    // Create triangles from center (fan triangulation)
    for (let i = 1; i <= numSegments; i++) {
      const next = i === numSegments ? 1 : i + 1
      indices.push(0, i, next)
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
    geo.setIndex(indices)

    const mat = new THREE.MeshBasicMaterial({
      color,
      opacity: isSelected ? 0.25 : 0.12,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
      depthTest: true,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1
    })

    return new THREE.Mesh(geo, mat)
  }, [satellite.noradId, satellite.latitude, satellite.longitude, satellite.altitude, color, isSelected])

  return (
    <group>
      {/* Coverage circle outline only - cleaner look */}
      <primitive object={footprint} />
      {/* Filled coverage area */}
      <primitive object={filledArea} />
    </group>
  )
}

// Orbit path visualization using real TLE propagation
// Simple line rendering with proper depth testing (hides behind globe naturally)
function OrbitPath({
  orbitPoints,
  color,
  isSelected
}: {
  orbitPoints: { lat: number; lon: number; alt: number }[]
  color: string
  isSelected: boolean
}) {
  const lineObject = useMemo(() => {
    if (orbitPoints.length < 2) {
      return null
    }

    // Convert to 3D points with proper altitude scaling
    const points = orbitPoints.map(({ lat, lon, alt }) => {
      const radius = 1 + (alt / EARTH_RADIUS_KM) * 1.2
      return latLonToVector3(lat, lon, radius)
    })

    const geo = new THREE.BufferGeometry()
    const positions = new Float32Array(points.flatMap(v => [v.x, v.y, v.z]))
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    // Simple line material - depth test handles occlusion naturally
    const mat = new THREE.LineBasicMaterial({
      color: color,
      opacity: isSelected ? 0.8 : 0.5,
      transparent: true,
      depthTest: true,
      depthWrite: false
    })

    return new THREE.Line(geo, mat)
  }, [orbitPoints, color, isSelected])

  if (!lineObject) return null

  return <primitive object={lineObject} />
}

/**
 * Lightweight satellite model for globe markers — plain materials only.
 * At 0.003 scale, procedural canvas textures are invisible and cause
 * lifecycle crashes (stale GPU references across mount/unmount cycles).
 * Full BlueBirdSatelliteHero is preserved for /dev/3d showcase.
 */
function SatelliteMarkerModel({
  generation = 'block1',
  scale = 0.003,
  selected = false,
}: {
  generation?: BlueBirdGeneration
  scale?: number
  selected?: boolean
}) {
  const config = GENERATION_CONFIGS[generation]
  const { arrayWidth, arrayLength, busDiameter, busHeight, panelThickness } = config
  const busSide = busDiameter * 0.45
  const busH = busSide * (busHeight / busDiameter)

  return (
    <group scale={[scale, scale, scale]}>
      {/* Solar panel array — flat dark blue box */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[arrayWidth, panelThickness, arrayLength]} />
        <meshPhysicalMaterial
          color={SAT_COLORS.solarCell}
          roughness={0.4}
          metalness={0.0}
          clearcoat={0.4}
        />
      </mesh>

      {/* Bus body — dark cube on top of array */}
      <mesh
        position={[0, panelThickness / 2 + busH / 2 + 0.01, 0]}
        castShadow
      >
        <boxGeometry args={[busSide, busH, busSide]} />
        <meshPhysicalMaterial
          color={SAT_COLORS.busBody}
          roughness={0.85}
          metalness={0.15}
        />
      </mesh>

      {/* Selection highlight */}
      {selected && (
        <mesh>
          <sphereGeometry args={[Math.max(arrayWidth, arrayLength) * 0.6, 16, 16]} />
          <meshBasicMaterial
            color="#06b6d4"
            transparent
            opacity={0.1}
            side={THREE.BackSide}
          />
        </mesh>
      )}
    </group>
  )
}

// Satellite marker (3D globe uses markers only - labels shown in selection UI)
function SatelliteMarker({
  satellite,
  isSelected,
  onClick,
  showOrbit,
  showCoverage,
  useDotMarker = false,
  coverageRadiusKm,
  orbitPoints
}: {
  satellite: SatelliteData
  isSelected: boolean
  onClick: () => void
  showOrbit: boolean
  showCoverage: boolean
  useDotMarker?: boolean
  coverageRadiusKm?: number
  orbitPoints?: { lat: number; lon: number; alt: number }[]
}) {
  const modelGroupRef = useRef<THREE.Group>(null)
  const groupRef = useRef<THREE.Group>(null)
  const { camera } = useThree()
  const [hovered, setHovered] = useState(false)
  const [visibility, setVisibility] = useState(1)
  const [cameraClose, setCameraClose] = useState(false)

  // Scale altitude: 500km -> more visible height above Earth
  // Increased multiplier from 0.5 to 1.2 for better visibility
  const altitudeScale = 1 + (satellite.altitude / 6371) * 1.2
  const position = latLonToVector3(satellite.latitude, satellite.longitude, altitudeScale)

  // Surface position for visibility calculation (where satellite points to on Earth)
  const surfacePosition = useMemo(() =>
    latLonToVector3(satellite.latitude, satellite.longitude, 1),
    [satellite.latitude, satellite.longitude]
  )

  // Camera-aware visibility (no scale animation)
  useFrame(() => {
    // Calculate visibility based on surface position facing camera
    if (groupRef.current) {
      // Get world position of surface point
      const worldSurface = surfacePosition.clone()
      groupRef.current.parent?.localToWorld(worldSurface)

      const viewDir = new THREE.Vector3().subVectors(camera.position, worldSurface).normalize()
      const normal = worldSurface.clone().normalize()
      const dot = normal.dot(viewDir)

      // Smooth visibility transition matching landmass shader
      const vis = THREE.MathUtils.smoothstep(dot, -0.1, 0.5)
      setVisibility(vis)

      // Check camera distance - show label when zoomed in close
      const camDist = camera.position.length()
      const isClose = camDist < 2.6 // Show labels when close
      if (isClose !== cameraClose) {
        setCameraClose(isClose)
      }

      // Apply visibility fade only to transparent materials (dot markers, lines)
      // 3D satellite models stay fully opaque
      groupRef.current.traverse((child) => {
        if ((child as THREE.Mesh).material) {
          const mat = (child as THREE.Mesh).material as THREE.MeshBasicMaterial | THREE.MeshStandardMaterial
          if (mat.transparent) {
            if (child.userData.originalOpacity === undefined) {
              child.userData.originalOpacity = mat.opacity ?? 1
            }
            mat.opacity = child.userData.originalOpacity * vis
          }
        }
      })
    }
  })

  // Calculate quaternion to orient satellite with array facing Earth
  // The BlueBird model has array in XZ plane, with +Y being "up" (bus side)
  // We want -Y (array face) to point toward Earth center
  const satelliteQuaternion = useMemo(() => {
    // The radial direction (outward from Earth center)
    const radialOut = position.clone().normalize()

    // We want the model's +Y axis to point radially outward (bus away from Earth)
    // This means array face (-Y) points toward Earth
    const modelUp = new THREE.Vector3(0, 1, 0)

    // Create quaternion that rotates modelUp to align with radialOut
    const quaternion = new THREE.Quaternion()
    quaternion.setFromUnitVectors(modelUp, radialOut)

    return quaternion
  }, [position])

  // Create line to Earth surface
  const surfaceLine = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    const surfacePoint = latLonToVector3(satellite.latitude, satellite.longitude, 1)
    const linePoints = [
      new THREE.Vector3(0, 0, 0),
      surfacePoint.clone().sub(position)
    ]
    geo.setFromPoints(linePoints)
    const mat = new THREE.LineBasicMaterial({
      color: SELECTION_COLOR,
      opacity: 0.15,
      transparent: true
    })
    return new THREE.Line(geo, mat)
  }, [satellite.latitude, satellite.longitude, position])

  // Determine dot size based on selection/hover state
  const dotSize = isSelected ? 0.04 : hovered ? 0.035 : 0.025

  return (
    <group ref={groupRef}>
      {/* Coverage footprint */}
      {showCoverage && (
        <CoverageFootprint
          satellite={satellite}
          isSelected={isSelected}
          color={SELECTION_COLOR}
          coverageRadiusKm={coverageRadiusKm ?? 0}
        />
      )}

      {/* Orbit path - only render if TLE data is available */}
      {showOrbit && orbitPoints && orbitPoints.length > 0 && (
        <OrbitPath
          orbitPoints={orbitPoints}
          color={isSelected ? SELECTION_COLOR : SATELLITE_MARKER_COLOR}
          isSelected={isSelected}
        />
      )}

      <group position={position}>
        {useDotMarker ? (
          <>
            {/* Simple orange dot marker */}
            <mesh>
              <sphereGeometry args={[dotSize, 16, 16]} />
              <meshBasicMaterial
                color={SELECTION_COLOR}
                opacity={visibility * (isSelected ? 1 : hovered ? 0.95 : 0.9)}
                transparent
              />
            </mesh>
            {/* Glow ring around dot */}
            {(isSelected || hovered) && (
              <mesh>
                <ringGeometry args={[dotSize * 1.3, dotSize * 1.8, 32]} />
                <meshBasicMaterial
                  color={SELECTION_COLOR}
                  opacity={visibility * 0.4}
                  transparent
                  side={THREE.DoubleSide}
                />
              </mesh>
            )}
          </>
        ) : (
          <>
            {/* 3D Satellite Model - oriented with array facing Earth */}
            <group ref={modelGroupRef} quaternion={satelliteQuaternion}>
              <SatelliteMarkerModel
                generation={getGenerationByNoradId(satellite.noradId)}
                scale={isSelected ? 0.004 : 0.003}
                selected={isSelected}
              />
            </group>

            {/* Selection glow effect */}
            {isSelected && (
              <mesh>
                <sphereGeometry args={[0.05, 12, 12]} />
                <meshBasicMaterial
                  color={SELECTION_COLOR}
                  opacity={0.25}
                  transparent
                />
              </mesh>
            )}
          </>
        )}

        {/* DOM-based click target + label — bypasses OrbitControls entirely */}
        {visibility > 0.15 && (
          <Html center style={{ pointerEvents: 'auto', opacity: visibility }}>
            <div
              onClick={(e) => { e.stopPropagation(); onClick() }}
              onMouseEnter={() => setHovered(true)}
              onMouseLeave={() => setHovered(false)}
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                cursor: 'pointer',
                position: 'relative',
              }}
            >
              {/* Label shown on hover/select/close-zoom */}
              {(hovered || isSelected || cameraClose) && (
                <div
                  className={`font-mono text-[10px] text-white bg-black/80 px-1.5 py-0.5 rounded whitespace-nowrap border ${isSelected ? 'border-[#FF6B35]/50' : 'border-white/[0.15]'}`}
                  style={{
                    position: 'absolute',
                    bottom: '100%',
                    marginBottom: '4px',
                    pointerEvents: 'none',
                  }}
                >
                  {satellite.name}
                </div>
              )}
            </div>
          </Html>
        )}

        {/* Line to Earth surface */}
        <primitive object={surfaceLine} />
      </group>
    </group>
  )
}

// Rotating container — auto-faces the satellite cluster on first load
function RotatingGroup({
  children,
  autoRotate,
  satellites = []
}: {
  children: React.ReactNode
  autoRotate: boolean
  satellites?: { longitude: number }[]
}) {
  const groupRef = useRef<THREE.Group>(null)
  const hasTilted = useRef(false)
  const targetY = useRef<number | null>(null)

  useFrame(() => {
    if (!groupRef.current) return

    // Fixed X tilt
    if (!hasTilted.current) {
      hasTilted.current = true
      groupRef.current.rotation.x = 0.3
    }

    // Continuously track satellite centroid longitude
    if (satellites.length > 0) {
      let sinSum = 0, cosSum = 0
      for (const sat of satellites) {
        const rad = sat.longitude * (Math.PI / 180)
        sinSum += Math.sin(rad)
        cosSum += Math.cos(rad)
      }
      const avgLonRad = Math.atan2(sinSum / satellites.length, cosSum / satellites.length)
      const desired = -(avgLonRad + Math.PI / 2)

      if (targetY.current === null) {
        groupRef.current.rotation.y = desired
        targetY.current = desired
      } else {
        targetY.current = desired
        let diff = targetY.current - groupRef.current.rotation.y
        while (diff > Math.PI) diff -= 2 * Math.PI
        while (diff < -Math.PI) diff += 2 * Math.PI
        groupRef.current.rotation.y += diff * 0.02
      }
    }

    if (autoRotate) {
      groupRef.current.rotation.y += 0.0008
    }
  })

  return (
    <group ref={groupRef}>
      {children}
    </group>
  )
}

// Main scene
function GlobeScene({
  satellites = [],
  selectedSatellite,
  onSelectSatellite,
  autoRotate = true,
  showOrbits = false,
  showCoverage = false,
  showCellGrid = false,
  useDotMarkers = false,
  coverageRadii,
  orbitPaths
}: Omit<Globe3DProps, 'className'>) {
  // Convert satellites to CellGrid format with coverage radius
  const cellGridSatellites = useMemo((): SatellitePosition[] => {
    return satellites.map(sat => ({
      lat: sat.latitude,
      lon: sat.longitude,
      altitudeKm: sat.altitude,
      coverageRadiusKm: coverageRadii?.[sat.noradId] ?? 0,
    }))
  }, [satellites, coverageRadii])

  return (
    <>
      <ambientLight intensity={0.25} color="#e8eeff" />
      <directionalLight position={[10, 8, 5]} intensity={1.2} color="#FFFAF0" />
      <directionalLight position={[-6, -4, 3]} intensity={0.4} color="#4a7aff" />
      <hemisphereLight args={['#1a1a2e', '#0a0a14', 0.3]} />

      <RotatingGroup autoRotate={autoRotate} satellites={satellites}>
        <WireframeEarth />
        <GridLines />
        <Landmasses />

        {/* Fixed Cell Grid - revealed by satellite footprints */}
        {/* Always mounted for instant toggle — visibility controlled via prop */}
        <CellGrid
          satellites={cellGridSatellites}
          globeRadius={1.004}
          detailLevel="AST_DENSITY"
          cellColor="#FF6B35"
          opacity={0.8}
          fadeEdge={0.2}
          visible={showCellGrid}
        />

        {satellites.map(sat => (
          <SatelliteMarker
            key={sat.noradId}
            satellite={sat}
            isSelected={sat.noradId === selectedSatellite}
            onClick={() => onSelectSatellite?.(sat.noradId)}
            showOrbit={showOrbits}
            showCoverage={showCoverage}
            useDotMarker={useDotMarkers}
            coverageRadiusKm={coverageRadii?.[sat.noradId]}
            orbitPoints={orbitPaths?.[sat.noradId]}
          />
        ))}
      </RotatingGroup>

      <OrbitControls
        enablePan={false}
        enableZoom={true}
        minDistance={1.8}
        maxDistance={5}
        autoRotate={false}
      />
    </>
  )
}

export function Globe3D({
  satellites = [],
  selectedSatellite,
  onSelectSatellite,
  autoRotate = false,  // Disabled by default for better UX
  showOrbits = false,
  showCoverage = false,
  showCellGrid,  // Follows showCoverage when not explicitly set
  className = '',
  useDotMarkers = false,
  paused = false,
  coverageRadii,
  orbitPaths
}: Globe3DProps) {
  return (
    <div className={`w-full h-full bg-[#030305] ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 3.2], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        frameloop={paused ? 'demand' : 'always'}
      >
        <color attach="background" args={['#030305']} />
        <GlobeScene
          satellites={satellites}
          selectedSatellite={selectedSatellite}
          onSelectSatellite={onSelectSatellite}
          autoRotate={autoRotate}
          showOrbits={showOrbits}
          showCoverage={showCoverage}
          showCellGrid={showCellGrid ?? showCoverage}
          useDotMarkers={useDotMarkers}
          coverageRadii={coverageRadii}
          orbitPaths={orbitPaths}
        />
      </Canvas>
    </div>
  )
}
