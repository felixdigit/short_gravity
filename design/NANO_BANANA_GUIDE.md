# Nano Banana (Gemini Image) — Prompting Guide

**Source**: [Google AI Official Docs](https://ai.google.dev/gemini-api/docs/image-generation)
**Last Updated**: January 25, 2026

---

## Models

| Model | ID | Resolution | Best For |
|-------|-----|------------|----------|
| **Gemini 2.5 Flash Image** | `gemini-2.5-flash-image` | 1024px | High-volume, fast generation |
| **Gemini 3 Pro Image** | `gemini-3-pro-image-preview` | 1K/2K/4K | Professional assets, complex scenes |

---

## Core Prompting Philosophy

**Stop using "tag soups"** like `dog, park, 4k, realistic`

**Start acting like a Creative Director** — Nano Banana understands intent, physics, and composition.

---

## The Formula

### Text-to-Image

```
Subject + Action + Environment + Art Style + Lighting + Details
```

| Element | Description | Example |
|---------|-------------|---------|
| Subject | Main character/object | "A satellite constellation" |
| Action | What it's doing | "orbiting Earth" |
| Environment | Location/background | "in low Earth orbit, stars visible" |
| Art Style | Visual aesthetic | "technical wireframe visualization" |
| Lighting | Light source/mood | "illuminated by Earth's glow" |
| Details | Specific additions | "cyan grid lines, orange highlights on active satellites" |

### Image Editing

```
Action/Change + Specific Element + Desired Style + Relevant Details
```

**Key editing words**: Add, Remove, Replace, Change, Adjust

---

## Best Practices (From Official Docs)

### 1. Be Hyper-Specific
- **Bad**: "A dashboard"
- **Good**: "A professional satellite tracking dashboard with dense terminal-style data panels, cyan grid overlays, monospace typography, multiple telemetry readouts showing altitude and velocity"

### 2. Provide Context
Explain the image's purpose:
- "This will be used as a UI reference for a financial terminal interface"
- "This is concept art for a space operations dashboard"

### 3. Use Photographic Terminology
- **Lens types**: 35mm, fisheye, telephoto, macro
- **Camera angles**: low angle, bird's eye, eye level, dutch angle
- **Lighting**: rim lighting, ambient, dramatic backlighting, soft diffused

### 4. Use Step-by-Step for Complex Scenes
```
Create an image with:
1. A dark control room environment
2. Multiple glowing monitors arranged in a semicircle
3. A central 3D holographic Earth display
4. Cyan and orange accent lighting
5. A single operator silhouette in the foreground
```

### 5. Semantic Negative Prompts
Don't say what you DON'T want. Describe the desired state positively:
- **Bad**: "No cluttered interface, no bright colors"
- **Good**: "Clean, minimal interface with muted dark tones"

### 6. Control Composition with Cinematic Language
- "Wide establishing shot"
- "Tight close-up on the data display"
- "Over-the-shoulder view of the operator"
- "Dutch angle creating tension"

---

## Aspect Ratios

| Ratio | Pixels (Flash) | Use Case |
|-------|----------------|----------|
| 1:1 | 1024x1024 | Social media, icons |
| 16:9 | 1536x864 | Dashboards, widescreen UI |
| 9:16 | 864x1536 | Mobile, vertical content |
| 4:3 | 1184x888 | Traditional display |
| 3:2 | 1256x838 | Photography style |
| 21:9 | 1536x672 | Ultrawide, cinematic |

---

## Prompt Templates for Short Gravity

### Dashboard UI Reference

```
Professional satellite operations dashboard interface, 16:9 widescreen format.

Layout:
- Left sidebar with navigation tabs
- Center: large 3D Earth visualization with orbital rings
- Right panels: dense telemetry data streams
- Top: status ticker with live metrics
- Bottom: timeline scrubber

Style:
- Deep black background (#0A0A0A)
- Cyan accent color for borders and grid lines
- Orange highlights for selected elements
- Monospace typography throughout
- Dense information layout like Bloomberg terminal

Effects:
- Subtle CRT scanlines
- Cyan glow on active panels
- Dark vignette on edges

Technical quality: Sharp, 4K detail, professional UI design
```

### Satellite Wireframe Diagram

```
Technical wireframe diagram of a satellite constellation deployment, engineering blueprint style.

Subject: BlueBird communication satellite array (5 satellites) inside a rocket fairing

Visual style:
- Cyan wireframe lines for structure
- Orange highlight on satellite payloads
- White annotation labels with leader lines
- Black void background
- Subtle grid pattern for scale reference

Composition:
- Isometric or slight 3/4 angle view
- Cutaway view showing interior satellite stack
- Dimension callouts and technical annotations

Quality: Ultra-sharp vector-style rendering, aerospace engineering aesthetic
```

### Mission Control Environment

```
Cinematic view of a satellite mission control room at night.

Environment:
- Dark room illuminated only by monitor glow
- Multiple curved display screens showing orbital data
- Central holographic Earth projection
- Operators silhouetted against screens

Lighting:
- Cyan light from monitors
- Orange accent lights on control panels
- Dramatic rim lighting on silhouettes
- No ambient light, pure screen glow

Mood: Professional, high-stakes, technological

Camera: Wide establishing shot, slight low angle
Quality: Photorealistic, cinematic color grading, 21:9 ultrawide
```

### Data Visualization Panel

```
Close-up of a financial terminal data panel, Bloomberg terminal aesthetic.

Content:
- Dense tabular data with monospace font
- Stock ticker-style scrolling header
- Color-coded metrics (green positive, red negative)
- Cyan borders separating sections
- Timestamp and update indicators

Style:
- Pure black background
- High contrast white text
- Minimal but precise design
- Professional, institutional feel

Aspect: 16:9
Quality: Crisp text rendering, pixel-perfect UI design
```

---

## Multi-Turn Refinement

Nano Banana excels at iterative editing. Instead of regenerating from scratch:

**Initial**: Generate base image

**Refinement examples**:
- "Make the satellites more prominent"
- "Add more data panels on the right side"
- "Change the cyan to a slightly more teal shade"
- "Increase the density of the grid pattern"
- "Add a subtle orange glow behind the Earth"

---

## Input Image Support

| Model | Max Images | Best Practice |
|-------|------------|---------------|
| Flash | 3 | Works best with 1-3 reference images |
| Pro | 14 | Up to 6 objects + 5 humans |

**Use cases**:
- Style transfer: "Apply this UI style to my dashboard concept"
- Character consistency: "Keep this satellite design across multiple angles"
- Composite scenes: "Combine these reference images into one composition"

---

## Token Costs

| Model | Resolution | Tokens |
|-------|------------|--------|
| Flash | 1024px (all ratios) | 1290 |
| Pro | 1K | 1120 |
| Pro | 2K | ~1500 |
| Pro | 4K | 2000 |

---

## Access Methods

1. **Gemini App** (web/mobile) — Select "Create Image" tool
2. **Google AI Studio** — Select Nano Banana in sidebar
3. **API** — Use `generateContent()` with image response modality

**Free tier**: ~100 images/day

---

## Key Reminders

1. **Describe scenes, don't list keywords**
2. **Be specific** — "cyan #06B6D4" beats "blue"
3. **Iterate conversationally** — Don't regenerate, refine
4. **Use photographic language** for composition control
5. **Context matters** — Tell it what the image is for
6. **Generated images include SynthID watermark**

---

*Refer to this guide before generating any Short Gravity visual assets.*
