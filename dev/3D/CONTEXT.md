# ASTS BlueBird 3D Model Development

## Reference Image
`reference-bluebird-official.png` — Official AST SpaceMobile render of Block 2 satellite

**Key observations from official reference:**
- Plus/cross silhouette — flat tile array with 3-tile corner cutouts
- Dark slate gray tiles (~#404555) with prominent silver frame grid between them
- Tile surface is matte with subtle texture, no busy sub-pattern
- Bus is compact near-black box with "AST" in orange, "SpaceMobile" in white
- Perimeter edges show serrated sandwich layers (aluminum/structural/solar)
- Frame lines are silver aluminum (~#a0a5b0), clearly visible
- Overall: clean, industrial, photorealistic

---

## Current Architecture

### Hero Model (Official Render Style)
```
short-gravity-web/components/earth/satellite/hero/
├── index.ts                        # Exports
├── BlueBirdSatelliteHero.tsx       # Main assembly
├── HeroTileArray.tsx               # Instanced tiles + silver frame grid
└── HeroBus.tsx                     # Clean dark box with branding
```

### Actual Model (Patent-Accurate)
```
short-gravity-web/components/earth/satellite/
├── index.ts                        # Exports
├── BlueBirdSatelliteV3.tsx         # Main assembly (cylindrical bus)
├── TileArray.tsx                   # Full rectangular grid (no cutouts)
├── SatelliteBus.tsx                # Cylindrical ControlSat bus
├── TapeSpringHinges.tsx            # Structural deployment hinges
├── config.ts                       # Generation specs, colors, materials
└── textures/
    └── generateSegmentTexture.ts   # Procedural PBR texture pipeline
```

### Shared Config (config.ts)
```typescript
COLORS = {
  solarCell: '#404555',       // Dark slate gray (hero tile face)
  segmentBase: '#B0B0B5',    // Brushed aluminum (actual tile face)
  busBody: '#1a1a1e',        // Near-black MLI thermal blanket
  honeycombCore: '#c8a850',  // Gold structural core (actual edges)
  tapeSpring: '#d0d0d2',     // Silver hinge strips
  busAccent: '#CCCCCC',      // Metallic trim
}
```

### Specifications

| Generation | Array | Tiles | Array Size | Bus | Mass |
|------------|-------|-------|------------|-----|------|
| BlueWalker 3 | 64 m² | 20×20 | 8m × 8m | 2.5m dia × 1.0m | 1,500 kg |
| Block 1 | 64 m² | 20×20 | 8m × 8m | 2.5m dia × 1.0m | 1,500 kg |
| Block 2 | 223 m² | 24×24 | 15m × 15m | 4.3m dia × 1.6m | 6,100 kg |

---

## Demo Pages

| URL | Content |
|-----|---------|
| `/bluebird-demo` | Re-exports `/dev/3d` |
| `/dev/3d` | Full viewer — actual/hero toggle, generation selector, reference galleries |

---

## Legacy Files (Deleted)

| File | Status |
|------|--------|
| `BlueBirdSatellite.tsx` | Deleted — V1, replaced by Hero + V3 |
| `BlueBirdSatelliteV2.tsx` | Deleted |
| `BlueBirdDemo.tsx` | Deleted |
| `BlueBirdDemoV2.tsx` | Deleted |

`getGenerationByNoradId()` moved to `config.ts`.

---

## Upgrade Paths (Researched Feb 2026)

### Path 1: Custom Shader Material (highest ceiling, pure code)

**Package:** `three-custom-shader-material` (CSM)
- Extends `MeshPhysicalMaterial` with custom GLSL
- Keeps all PBR lighting, clearcoat, anisotropy, env reflections
- Grid pattern computed per-pixel at infinite resolution
- Anti-aliased via `fwidth()` — never blurs at any zoom

**Key technique — anti-aliased grid lines:**
```glsl
vec2 coord = vUv * uGridScale;
vec2 grid = abs(fract(coord - 0.5) - 0.5) / fwidth(coord);
float line = min(grid.x, grid.y);
float gridFactor = 1.0 - min(line, 1.0);
```

**CSM output variables for PBR:**
- `csm_DiffuseColor` — custom color WITH shading preserved
- `csm_Roughness` — per-pixel roughness (grid lines smoother than cells)
- `csm_Metalness` — per-pixel metalness (silver grid = metallic)
- `csm_Clearcoat`, `csm_Iridescence`, `csm_AO`, etc.

**Full fragment shader concept:**
```glsl
uniform float uGridScale;      // 6.0 for 6x6
uniform float uLineWidth;      // 0.02
uniform vec3 uCellColor;       // #404555
uniform vec3 uGridColor;       // #a0a5b0
uniform float uCellVariation;  // 0.03

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
  vec2 scaledUv = vUv * uGridScale;
  vec2 cellId = floor(scaledUv);
  float cellNoise = hash(cellId) * uCellVariation;

  // Anti-aliased grid
  vec2 gridUv = abs(fract(scaledUv - 0.5) - 0.5);
  vec2 deriv = fwidth(scaledUv);
  vec2 lineAA = deriv * 1.5;
  vec2 lines = smoothstep(uLineWidth + lineAA, uLineWidth - lineAA, gridUv);
  float gridFactor = 1.0 - min(lines.x, 1.0) * min(lines.y, 1.0);

  // Sub-cell busbar lines
  vec2 subUv = fract(scaledUv);
  vec2 subDeriv = fwidth(subUv);
  float centerX = smoothstep(0.005 + subDeriv.x, 0.005 - subDeriv.x, abs(subUv.x - 0.5));
  float centerY = smoothstep(0.005 + subDeriv.y, 0.005 - subDeriv.y, abs(subUv.y - 0.5));
  float subGrid = max(centerX, centerY) * 0.15;

  vec3 cellColorVaried = uCellColor + vec3(cellNoise - uCellVariation * 0.5);
  vec3 color = mix(cellColorVaried, uGridColor, gridFactor);
  color = mix(color, uGridColor * 0.7, subGrid);

  csm_DiffuseColor = vec4(color, 1.0);
  csm_Roughness = mix(0.5, 0.25, gridFactor);
  csm_Metalness = mix(0.05, 0.6, gridFactor);
}
```

**Implementation:**
```bash
cd short-gravity-web && npm install three-custom-shader-material
```
Then create `HeroTileShader.tsx` using CSM with the above GLSL.

**References:**
- [CSM GitHub](https://github.com/FarazzShaikh/THREE-CustomShaderMaterial)
- [Anti-aliased grid — Made by Evan](https://madebyevan.com/shaders/grid/)
- [Best Darn Grid Shader — Ben Golus](https://bgolus.medium.com/the-best-darn-grid-shader-yet-727f9278b9d8)

---

### Path 2: AI-Generated GLB Model (fastest to photorealistic)

Feed reference image to AI 3D generator → get GLB → import with `npx gltfjsx`.

**Ranked options:**

| Tool | Quality | Cost | API |
|------|---------|------|-----|
| **Hyper3D Rodin Gen-2** | 9/10 | 7-day free trial, ~$0.40/gen on fal.ai | REST API (curl) |
| **Meshy 6** | 7/10 | Free tier = 3 attempts | REST API + MCP server |
| **TRELLIS.2** (Microsoft) | 7/10 | Free (MIT, open source) | HuggingFace Space / Docker |
| **Tripo3D v2.5** | 6/10 | Free tier = 10 attempts | Python SDK (`pip install tripo3d`) |

**Workflow:**
```bash
# Generate (example: Meshy)
curl -X POST https://api.meshy.ai/openapi/v1/image-to-3d \
  -H "Authorization: Bearer $MESHY_API_KEY" \
  -d '{"image_url": "...", "ai_model": "meshy-6", "enable_pbr": true}'

# Download GLB, convert to R3F component
npx gltfjsx satellite.glb --types --transform --draco

# Result: typed React component with useGLTF hook
# Replace AI materials with our PBR pipeline
```

**Meshy MCP Server** for direct Claude Code integration:
```json
{
  "mcpServers": {
    "meshy": {
      "command": "npx",
      "args": ["-y", "meshy-ai-mcp-server"],
      "env": { "MESHY_API_KEY": "your_key" }
    }
  }
}
```

**Risk:** BlueBird's extreme flat aspect ratio is unusual for AI 3D tools. May need multiple attempts.

---

### Path 3: Quick Wins (add to any approach)

**Iridescence on solar panels:**
```tsx
iridescence={0.15}
iridescenceIOR={1.8}
iridescenceThicknessRange={[100, 250]}
```
Real PV cells have anti-reflective coating that produces blue-purple angle shift.

**Dual SSAO:**
```tsx
<SSAO radius={0.5} intensity={1.5} />   // Coarse: tile-to-bus shadows
<SSAO radius={0.08} intensity={2.0} />  // Fine: grid crevice detail
```

**MeshReflectorMaterial** for product-shot floor:
```tsx
import { MeshReflectorMaterial } from '@react-three/drei'
<mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -3, 0]}>
  <planeGeometry args={[80, 80]} />
  <MeshReflectorMaterial blur={[300, 100]} resolution={1024}
    mixStrength={0.5} color="#050505" metalness={0.5} />
</mesh>
```

**Space HDRI** instead of "city" preset — use "night" or custom space environment.

**MeshTransmissionMaterial** for star tracker glass lens:
```tsx
<MeshTransmissionMaterial transmission={0.95} thickness={0.5}
  chromaticAberration={0.02} ior={1.5} color="#0a0a12" />
```

**Per-instance variation** via `InstancedBufferAttribute`:
```tsx
geometry.setAttribute('aVariation',
  new THREE.InstancedBufferAttribute(variationData, 2))
// In CSM shader: csm_DiffuseColor.rgb += vVariation.x;
```

---

## Commands

```bash
# Dev server
cd short-gravity-web && npm run dev

# Navigate to demo
open http://localhost:3000/dev/3d

# Install CSM (for shader path)
cd short-gravity-web && npm install three-custom-shader-material

# Convert GLB to R3F (for AI model path)
npx gltfjsx model.glb --types --transform --draco
```
