#!/usr/bin/env python3
"""
Gemini Image Generator for Short Gravity

Generate visual assets with baked-in Short Gravity aesthetics.
Uses Google's Gemini 2.0 Flash image generation.

Usage:
    python3 image_generator.py --template dashboard --aspect 16:9 --output ./output.png
    python3 image_generator.py --prompt "Custom prompt" --aspect 1:1 --output ./custom.png
    python3 image_generator.py --template banner --aspect 21:9 --upload
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from datetime import datetime
from typing import Optional

# Requires: pip install google-genai
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed")
    print("Run: pip install google-genai")
    sys.exit(1)

from storage_utils import upload_document, log


# =============================================================================
# Style Defaults - Short Gravity Design System V4
# Source: globals.css + FIGMA_SPECS.md
# Aesthetic: NASA Eyes + Bloomberg Terminal
# =============================================================================

STYLE_DEFAULTS = {
    # Backgrounds
    "void_black": "#030305",      # Deepest black - page bg
    "space_dark": "#0A0A0F",      # Primary surface
    "nebula_depth": "#0D1117",    # Card backgrounds
    # Brand accents
    "asts_orange": "#FF6B35",     # Primary - trajectories, highlights, selections
    "origin_blue": "#0077C8",     # Secondary - interactive, links
    "amber": "#D4A574",           # Headers, titles, active states
    # Status
    "status_nominal": "#22C55E",  # Green - operational
    "status_warning": "#EAB308",  # Yellow - caution
    "status_critical": "#EF4444", # Red - critical
    # Text
    "text_primary": "#FFFFFF",    # Pure white
    "text_secondary": "#E5E7EB",  # Bright gray
    "text_muted": "#71717A",      # Subtle
    # UI
    "border": "#1a1a1a",          # All borders
    "border_active": "#06B6D4",   # Cyan for active states only
}

STYLE_SUFFIX = f"""

Art direction (Short Gravity Design System V4):

Colors:
- Background: true black ({STYLE_DEFAULTS['void_black']}) to deep space ({STYLE_DEFAULTS['space_dark']})
- Primary accent: ASTS Orange ({STYLE_DEFAULTS['asts_orange']}) for trajectories, orbital paths, highlights, selected elements
- Secondary accent: Origin Blue ({STYLE_DEFAULTS['origin_blue']}) for interactive elements, links, secondary data
- Headers/titles: Amber ({STYLE_DEFAULTS['amber']})
- Active borders: Cyan ({STYLE_DEFAULTS['border_active']}) used sparingly
- Status indicators: Green ({STYLE_DEFAULTS['status_nominal']}) nominal, Yellow ({STYLE_DEFAULTS['status_warning']}) warning, Red ({STYLE_DEFAULTS['status_critical']}) critical
- Text: Pure white ({STYLE_DEFAULTS['text_primary']}) for key data, gray hierarchy for secondary

Typography:
- JetBrains Mono monospace font throughout
- Uppercase labels with wide letter-spacing
- Dense information layout, Bloomberg terminal density

Aesthetic:
- NASA Eyes + Bloomberg Terminal fusion
- Mission control operations feel
- Sharp corners (no rounded borders)
- Aerospace engineering precision
- High information density
- Dark vignette on edges

Effects:
- Subtle CRT scanlines (optional)
- Orange glow on orbital trajectories
- Green pulse on live/nominal status
- Cyan border glow on active/selected panels

Quality: Professional UI design, 4K sharp detail, photorealistic digital interface
"""


# =============================================================================
# Aspect Ratio Mapping
# =============================================================================

ASPECT_RATIOS = {
    "1:1": (1024, 1024),
    "16:9": (1536, 864),
    "9:16": (864, 1536),
    "4:3": (1152, 864),
    "21:9": (1792, 768),
}


# =============================================================================
# Template Functions
# =============================================================================

def template_dashboard() -> str:
    """Satellite operations dashboard UI."""
    return """
Professional satellite operations dashboard interface, NASA Eyes meets Bloomberg Terminal.

Subject: Multi-panel mission control interface for AST SpaceMobile constellation tracking.

Layout:
- Left sidebar: navigation tabs with amber headers
- Center: 3D Earth globe with orbital paths traced in ASTS Orange (#FF6B35)
- Right panels: dense telemetry data streams in monospace
- Top: status ticker with live metrics, green pulse indicators
- Bottom: timeline scrubber with upcoming events

Details:
- BlueBird satellite constellation visualization with orange orbital rings
- Connection beams to ground stations in Origin Blue (#0077C8)
- Data readouts: altitude, velocity, inclination, RAAN values
- Panel headers in amber (#D4A574), uppercase, JetBrains Mono
- Status indicators: green (● LIVE), yellow (● DEPLOYING), red (● OFFLINE)
- Sharp corners on all panels, 1px borders (#1a1a1a)
- Cyan border glow (#06B6D4) on selected/active panel only
""" + STYLE_SUFFIX


def template_satellite_diagram() -> str:
    """Technical wireframe/blueprint style."""
    return """
Technical engineering blueprint of AST SpaceMobile BlueBird satellite.

Subject: Detailed satellite wireframe diagram showing the world's largest commercial phased-array antenna.

Visual style:
- White wireframe lines for structure on true black background
- Orange (#FF6B35) highlight on the 64 square meter antenna array
- Amber (#D4A574) annotation labels with leader lines
- Subtle grid pattern for scale reference

Components to show:
- Massive phased-array antenna panel (main feature, 693 sq ft / 64 sq m)
- Solar array wings extended (providing 2.5+ kW power)
- Spacecraft bus with labeled subsystems
- Dimension callouts and technical annotations
- Cross-section inset showing antenna feed architecture
- Specification table: mass, power, dimensions, frequency bands

Composition: Isometric 3/4 angle view, aerospace engineering aesthetic
Quality: Ultra-sharp vector-style rendering, technical documentation feel
""" + STYLE_SUFFIX


def template_data_panel() -> str:
    """Bloomberg-style data visualization panel."""
    return """
Bloomberg terminal style financial data panel for ASTS (AST SpaceMobile).

Subject: Dense data visualization interface, institutional trading terminal aesthetic.

Layout: Multiple data cards in tight grid, sharp corners, 1px borders (#1a1a1a)

Content panels:
- Stock price chart: white candlesticks, orange moving averages, volume bars below
- Key metrics card: market cap, enterprise value, cash position, burn rate
- Satellite deployment tracker: constellation progress bar
- News ticker: recent headlines with timestamps
- Analyst ratings: distribution chart
- Upcoming catalysts: earnings, launches, regulatory milestones
- Options flow: unusual activity highlights

Visual style:
- True black background (#000000)
- Panel headers: amber (#D4A574), 10px JetBrains Mono, uppercase
- Data values: white (#CCCCCC), monospace
- Labels: gray (#666666)
- Positive values: green (#22C55E)
- Negative values: red (#EF4444)
- Live panels: green border glow, "● LIVE" badge
""" + STYLE_SUFFIX


def template_mission_control() -> str:
    """Cinematic control room environment."""
    return """
Cinematic view of AST SpaceMobile mission control during satellite deployment operations.

Subject: Modern satellite operations center, NASA-style environment.
Perspective: Wide establishing shot, slight low angle for gravitas.

Scene elements:
- Dark room illuminated only by monitor glow
- Multiple operator workstations with curved displays
- Large main screen: 3D Earth with BlueBird constellation, orange orbital paths
- Side screens: telemetry dashboards, signal coverage maps, weather data
- Operators silhouetted against screens
- Mission clock / countdown timer visible
- "AST SpaceMobile" or "Short Gravity" subtle branding

Lighting:
- Screens cast orange and blue light into the room
- Green glow from nominal status indicators
- Dramatic rim lighting on operator silhouettes
- No ambient room lighting, pure screen illumination
- Dark vignette on edges

Mood: Professional, high-stakes, technological precision
Camera: 21:9 ultrawide, cinematic color grading
""" + STYLE_SUFFIX


def template_banner() -> str:
    """Wide social media or website banner."""
    return """
Ultra-wide cinematic banner: AST SpaceMobile BlueBird constellation over Earth.

Subject: Space-based cellular network visualization, hero image for Short Gravity.
Composition: Panoramic view of Earth's curvature with satellite constellation.

Scene:
- Earth horizon at bottom third, city lights visible on night side
- BlueBird satellites in orbital formation, connected by subtle orange lines
- Ground station beams in Origin Blue (#0077C8) connecting to satellites
- Coverage footprint visualized as transparent orange overlay on Earth
- Orbital trajectory rings in ASTS Orange (#FF6B35)
- Negative space in corner for logo/text overlay

Atmosphere:
- Terminator line (day/night boundary) visible on Earth
- Deep space black above, stars visible
- Earth's atmosphere as thin blue line at horizon
- Subtle lens flare from sun position
- Professional, institutional feel (not sci-fi fantasy)

Quality: Photorealistic rendering, cinematic 21:9 aspect, NASA imagery quality
""" + STYLE_SUFFIX


TEMPLATES = {
    "dashboard": template_dashboard,
    "satellite_diagram": template_satellite_diagram,
    "data_panel": template_data_panel,
    "mission_control": template_mission_control,
    "banner": template_banner,
}


# =============================================================================
# Image Generation
# =============================================================================

def build_prompt(template: Optional[str], custom_prompt: Optional[str]) -> str:
    """Build the final prompt from template or custom input."""
    if custom_prompt:
        # Custom prompt still gets style suffix
        return custom_prompt + STYLE_SUFFIX

    if template and template in TEMPLATES:
        return TEMPLATES[template]()

    raise ValueError(f"Unknown template: {template}. Available: {list(TEMPLATES.keys())}")


def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    model_id: str = "gemini-2.0-flash-exp-image-generation",
) -> bytes:
    """
    Generate image using Gemini API.

    Returns raw PNG bytes.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    # Get dimensions for aspect ratio
    width, height = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["16:9"])

    # Add aspect ratio instruction to prompt
    full_prompt = f"{prompt}\n\nImage dimensions: {width}x{height} pixels, aspect ratio {aspect_ratio}"

    log(f"Generating image with {model_id}...")
    log(f"Aspect ratio: {aspect_ratio} ({width}x{height})")

    # Initialize client
    client = genai.Client(api_key=api_key)

    # Generate image with response modalities
    response = client.models.generate_content(
        model=model_id,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # Extract image from response
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            mime_type = part.inline_data.mime_type
            log(f"Received image: {mime_type}")
            return part.inline_data.data

    raise RuntimeError("No image generated in response")


def save_image(image_bytes: bytes, output_path: str) -> str:
    """Save image bytes to local file."""
    # Create directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    log(f"Saved: {output_path} ({len(image_bytes):,} bytes)")
    return output_path


def upload_image(
    image_bytes: bytes,
    template: str,
    aspect_ratio: str,
) -> dict:
    """Upload image to Supabase Storage."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{template}/{aspect_ratio.replace(':', 'x')}/{timestamp}.png"

    result = upload_document(
        bucket="generated-images",
        path=path,
        content=image_bytes,
        content_type="image/png",
    )

    if result.get("success"):
        log(f"Uploaded: generated-images/{path}")
    else:
        log(f"Upload failed: {result.get('error')}")

    return result


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate Short Gravity visual assets with Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 image_generator.py --template dashboard --aspect 16:9 --output ./dashboard.png
  python3 image_generator.py --prompt "Satellite in orbit" --aspect 1:1 --output ./sat.png
  python3 image_generator.py --template banner --aspect 21:9 --upload
        """,
    )

    parser.add_argument(
        "--template",
        choices=list(TEMPLATES.keys()),
        help="Use a predefined template",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Custom prompt (overrides template)",
    )
    parser.add_argument(
        "--aspect",
        choices=list(ASPECT_RATIOS.keys()),
        default="16:9",
        help="Aspect ratio (default: 16:9)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: ./generated_{timestamp}.png)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload to Supabase Storage instead of local save",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-2.0-flash-exp-image-generation",
        help="Gemini model ID (default: gemini-2.0-flash-exp-image-generation)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.template and not args.prompt:
        parser.error("Either --template or --prompt is required")

    # Build prompt
    try:
        prompt = build_prompt(args.template, args.prompt)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Generate image
    try:
        image_bytes = generate_image(
            prompt=prompt,
            aspect_ratio=args.aspect,
            model_id=args.model,
        )
    except Exception as e:
        print(f"ERROR: Generation failed - {e}")
        sys.exit(1)

    # Save or upload
    if args.upload:
        template_name = args.template or "custom"
        result = upload_image(image_bytes, template_name, args.aspect)
        if not result.get("success"):
            sys.exit(1)
    else:
        if args.output:
            output_path = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"./generated_{timestamp}.png"

        save_image(image_bytes, output_path)

    log("Done.")


if __name__ == "__main__":
    main()
