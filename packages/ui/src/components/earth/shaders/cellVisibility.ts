/**
 * Cell Visibility Shaders
 *
 * GPU-based visibility calculation for hexagonal cell grid.
 * Cells are revealed when within satellite coverage footprint.
 *
 * Enhanced with wireframe rendering using distance-from-center approach.
 * Each vertex has a 'distFromCenter' attribute (0 for center, 1 for corners).
 */

export const cellVertexShader = /* glsl */ `
  // Vertex attributes
  attribute float cellIndex;
  attribute vec3 barycentric;  // Barycentric coords for wireframe edge detection

  // Varyings passed to fragment shader
  varying vec3 vModelPosition;  // Position in model space (before rotation)
  varying vec3 vNormal;
  varying float vCellIndex;
  varying vec3 vBarycentric;

  void main() {
    vCellIndex = cellIndex;
    vBarycentric = barycentric;
    vNormal = normalize(normalMatrix * normal);

    // Model position (local space) - NOT transformed by modelMatrix
    // This ensures satellite positions can be compared in the same coordinate system
    // since satellites are defined in lat/lon which maps to model space
    vModelPosition = position;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const cellFragmentShader = /* glsl */ `
  precision highp float;

  // Maximum satellites we support (increased for future constellation growth)
  #define MAX_SATELLITES 20

  // Uniforms
  uniform vec3 uSatellitePositions[MAX_SATELLITES];  // Normalized positions on unit sphere
  uniform float uCoverageRadii[MAX_SATELLITES];       // Coverage radius as angle (radians)
  uniform int uActiveSatellites;
  uniform vec3 uCellColor;
  uniform float uOpacity;
  uniform float uFadeEdge;  // Percentage of edge to fade (0.0 - 0.5)
  uniform float uLineWidth;  // Wireframe line thickness (0.0 - 0.5)
  uniform bool uWireframe;   // Toggle wireframe vs filled mode

  // Varyings from vertex shader
  varying vec3 vModelPosition;  // Position in model space (local coordinates)
  varying vec3 vNormal;
  varying float vCellIndex;
  varying vec3 vBarycentric;  // Barycentric coordinates for edge detection

  // Calculate angle between two points on sphere (great circle distance)
  float sphericalAngle(vec3 p1, vec3 p2) {
    vec3 n1 = normalize(p1);
    vec3 n2 = normalize(p2);
    return acos(clamp(dot(n1, n2), -1.0, 1.0));
  }

  // Edge detection using barycentric coordinates
  // Returns 1.0 on edges, 0.0 in interior
  float edgeFactor(vec3 bary, float width) {
    vec3 d = fwidth(bary);
    vec3 a3 = smoothstep(vec3(0.0), d * width, bary);
    return 1.0 - min(min(a3.x, a3.y), a3.z);
  }

  void main() {
    // Normalize model position to get point on unit sphere
    // Using model space ensures alignment with satellite positions
    // (both are defined in lat/lon mapped to unit sphere coordinates)
    vec3 cellPoint = normalize(vModelPosition);

    // Check visibility against all satellites
    float maxVisibility = 0.0;

    for (int i = 0; i < MAX_SATELLITES; i++) {
      if (i >= uActiveSatellites) break;

      vec3 satPoint = uSatellitePositions[i];
      float coverageAngle = uCoverageRadii[i];

      // Calculate angular distance from cell to satellite nadir
      float angularDist = sphericalAngle(cellPoint, satPoint);

      // Check if within coverage
      if (angularDist <= coverageAngle) {
        // Calculate visibility with soft edge
        float edgeStart = coverageAngle * (1.0 - uFadeEdge);

        if (angularDist <= edgeStart) {
          maxVisibility = 1.0;
          break;  // Fully visible, no need to check more
        } else {
          // Smooth fade at edge using smoothstep
          float visibility = 1.0 - smoothstep(edgeStart, coverageAngle, angularDist);
          maxVisibility = max(maxVisibility, visibility);
        }
      }
    }

    // Discard if not visible at all (not within any satellite coverage)
    if (maxVisibility < 0.01) {
      discard;
    }

    // Wireframe rendering using barycentric coordinates
    // Each triangle in the hex fan has barycentric coords where:
    // - Component 0 (x) = 1 at center vertex, 0 at corners
    // - Component 1 (y) = 1 at first corner, 0 elsewhere
    // - Component 2 (z) = 1 at second corner, 0 elsewhere
    // We only want to render the OUTER edge (between the two corners, where x=0)
    float wireframeFactor = 1.0;
    if (uWireframe) {
      // Detect proximity to the outer edge only (where barycentric.x approaches 0)
      // This is the edge opposite the center vertex
      float outerEdgeDist = vBarycentric.x;  // 0 at outer edge, 1 at center

      // Width scaled by screen-space derivatives for consistent thickness
      float edgeWidth = uLineWidth * 1.5;
      float d = fwidth(outerEdgeDist) * edgeWidth;

      // Only show outer edge (small x value means near outer edge)
      wireframeFactor = 1.0 - smoothstep(0.0, d * 30.0, outerEdgeDist);

      if (wireframeFactor < 0.01) {
        discard;
      }
    }

    // Apply cell color with visibility-based opacity
    float finalOpacity = uOpacity * maxVisibility * wireframeFactor;

    // Slight variation based on cell index for visual interest
    float indexVariation = 0.95 + 0.05 * fract(sin(vCellIndex * 12.9898) * 43758.5453);

    gl_FragColor = vec4(uCellColor * indexVariation, finalOpacity);
  }
`;

// Uniforms interface for TypeScript - uses IUniform pattern for Three.js compatibility
export interface CellShaderUniforms {
  [uniform: string]: { value: unknown };
  uSatellitePositions: { value: Float32Array };
  uCoverageRadii: { value: Float32Array };
  uActiveSatellites: { value: number };
  uCellColor: { value: [number, number, number] };
  uOpacity: { value: number };
  uFadeEdge: { value: number };
  uLineWidth: { value: number };
  uWireframe: { value: boolean };
}

// Create default uniforms
export function createCellShaderUniforms(): CellShaderUniforms {
  return {
    uSatellitePositions: { value: new Float32Array(60) }, // 20 satellites * 3 components
    uCoverageRadii: { value: new Float32Array(20) },
    uActiveSatellites: { value: 0 },
    uCellColor: { value: [0.914, 0.561, 0.314] }, // Orange #e98f50
    uOpacity: { value: 0.6 },
    uFadeEdge: { value: 0.2 },
    uLineWidth: { value: 0.12 }, // Wireframe line thickness
    uWireframe: { value: true }, // Enable wireframe by default
  };
}

/**
 * Convert coverage radius in km to angular radius in radians
 * For a satellite at given altitude
 */
export function coverageKmToRadians(coverageRadiusKm: number): number {
  const EARTH_RADIUS_KM = 6371;
  // Arc length = radius * angle, so angle = arc / radius
  return coverageRadiusKm / EARTH_RADIUS_KM;
}

/**
 * Convert lat/lon to normalized 3D position
 */
export function latLonToNormalized3D(lat: number, lon: number): [number, number, number] {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  return [
    -Math.sin(phi) * Math.cos(theta),
    Math.cos(phi),
    Math.sin(phi) * Math.sin(theta),
  ];
}
