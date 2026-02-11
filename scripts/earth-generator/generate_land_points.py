#!/usr/bin/env python3
"""
Generate Earth landmass points using Fibonacci Sphere distribution
filtered against a NASA land mask image.

This produces the SpaceX-style dotted globe effect where points
only appear on land masses.

Algorithm:
1. Generate N evenly-spaced points on a sphere using Fibonacci distribution
2. Convert each 3D point to lat/lon coordinates
3. Map lat/lon to UV coordinates on the land mask image
4. Keep only points where the pixel is white (land)

Output: JSON file with lat/lon coordinates for use in Three.js/SVG visualizations
"""

import json
import math
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

import urllib.request
import os


def download_land_mask():
    """Download NASA land mask if not present."""
    mask_path = Path(__file__).parent / "land_mask.png"

    if mask_path.exists():
        print(f"✓ Land mask already exists: {mask_path}")
        return mask_path

    # NASA Blue Marble land mask (simple black/white)
    # Alternative: use a simple equirectangular black/white Earth image
    url = "https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57752/land_shallow_topo_2048.jpg"

    print(f"Downloading land mask from NASA...")
    try:
        urllib.request.urlretrieve(url, mask_path)
        print(f"✓ Downloaded to {mask_path}")

        # Convert to grayscale for easier processing
        img = Image.open(mask_path).convert('L')
        img.save(mask_path)
        print(f"✓ Converted to grayscale")
        return mask_path
    except Exception as e:
        print(f"✗ Failed to download: {e}")
        print("Creating synthetic land mask instead...")
        return create_synthetic_mask(mask_path)


def create_synthetic_mask(mask_path):
    """Create a synthetic land mask based on approximate continent boundaries."""
    print("Generating synthetic land mask from continent polygons...")

    width, height = 2048, 1024
    img = Image.new('L', (width, height), 0)  # Black background (ocean)
    pixels = img.load()

    # Define approximate continent boundaries as lat/lon ranges
    # These are rough rectangles - good enough for point generation
    continents = [
        # North America
        {"lat": (25, 85), "lon": (-170, -50)},
        # Central America
        {"lat": (7, 25), "lon": (-120, -60)},
        # South America
        {"lat": (-56, 15), "lon": (-82, -34)},
        # Europe
        {"lat": (35, 72), "lon": (-25, 65)},
        # Africa
        {"lat": (-35, 37), "lon": (-18, 52)},
        # Asia (main)
        {"lat": (5, 77), "lon": (25, 180)},
        # Asia (far east Russia)
        {"lat": (40, 77), "lon": (-180, -170)},
        # India subcontinent
        {"lat": (5, 35), "lon": (65, 95)},
        # Southeast Asia
        {"lat": (-10, 25), "lon": (95, 145)},
        # Indonesia
        {"lat": (-10, 5), "lon": (95, 140)},
        # Australia
        {"lat": (-45, -10), "lon": (112, 155)},
        # New Zealand
        {"lat": (-47, -34), "lon": (166, 179)},
        # Japan
        {"lat": (30, 46), "lon": (128, 146)},
        # UK/Ireland
        {"lat": (50, 60), "lon": (-11, 2)},
        # Iceland
        {"lat": (63, 67), "lon": (-25, -13)},
        # Greenland
        {"lat": (59, 84), "lon": (-75, -10)},
        # Madagascar
        {"lat": (-26, -12), "lon": (43, 51)},
        # Philippines
        {"lat": (5, 20), "lon": (117, 127)},
        # Taiwan
        {"lat": (22, 26), "lon": (120, 122)},
        # Sri Lanka
        {"lat": (6, 10), "lon": (79, 82)},
        # Caribbean (approximate)
        {"lat": (10, 25), "lon": (-85, -60)},
        # Papua New Guinea
        {"lat": (-10, 0), "lon": (140, 155)},
    ]

    for region in continents:
        lat_min, lat_max = region["lat"]
        lon_min, lon_max = region["lon"]

        # Handle wraparound for regions crossing the date line
        if lon_min > lon_max:
            # Split into two regions
            regions_to_fill = [
                (lat_min, lat_max, lon_min, 180),
                (lat_min, lat_max, -180, lon_max)
            ]
        else:
            regions_to_fill = [(lat_min, lat_max, lon_min, lon_max)]

        for lat1, lat2, lon1, lon2 in regions_to_fill:
            # Convert to pixel coordinates
            x1 = int((lon1 + 180) / 360 * width)
            x2 = int((lon2 + 180) / 360 * width)
            y1 = int((90 - lat2) / 180 * height)
            y2 = int((90 - lat1) / 180 * height)

            # Fill rectangle
            for y in range(max(0, y1), min(height, y2)):
                for x in range(max(0, x1), min(width, x2)):
                    pixels[x, y] = 255  # White = land

    img.save(mask_path)
    print(f"✓ Saved synthetic mask to {mask_path}")
    return mask_path


def fibonacci_sphere(num_points: int):
    """
    Generate evenly distributed points on a unit sphere using Fibonacci spiral.
    Returns list of (x, y, z) tuples.
    """
    points = []
    phi = math.pi * (math.sqrt(5) - 1)  # Golden angle in radians

    for i in range(num_points):
        y = 1 - (i / (num_points - 1)) * 2  # y goes from 1 to -1
        radius = math.sqrt(1 - y * y)  # radius at y

        theta = phi * i  # golden angle increment

        x = math.cos(theta) * radius
        z = math.sin(theta) * radius

        points.append((x, y, z))

    return points


def cartesian_to_latlon(x: float, y: float, z: float):
    """Convert 3D Cartesian coordinates to lat/lon (degrees)."""
    lat = math.asin(y) * 180 / math.pi
    lon = math.atan2(z, x) * 180 / math.pi
    return lat, lon


def latlon_to_uv(lat: float, lon: float, width: int, height: int):
    """Convert lat/lon to image UV coordinates (pixel position)."""
    u = (lon + 180) / 360 * width
    v = (90 - lat) / 180 * height
    return int(u) % width, int(v) % height


def is_land(img, lat: float, lon: float, threshold: int = 50):
    """Check if a lat/lon coordinate is on land based on the mask image."""
    width, height = img.size
    x, y = latlon_to_uv(lat, lon, width, height)
    pixel = img.getpixel((x, y))

    # Handle both grayscale and RGB images
    if isinstance(pixel, tuple):
        brightness = sum(pixel[:3]) / 3
    else:
        brightness = pixel

    return brightness > threshold


def generate_land_points(num_sphere_points: int = 8000, threshold: int = 50):
    """
    Generate land points using Fibonacci sphere filtered by land mask.

    Args:
        num_sphere_points: Total points to generate on sphere (more = denser)
        threshold: Brightness threshold for land detection (0-255)

    Returns:
        List of {lat, lon} dictionaries for land points
    """
    # Get or create land mask
    mask_path = download_land_mask()
    img = Image.open(mask_path).convert('L')

    print(f"Land mask size: {img.size}")
    print(f"Generating {num_sphere_points} Fibonacci sphere points...")

    # Generate evenly distributed points
    sphere_points = fibonacci_sphere(num_sphere_points)

    # Filter to keep only land points
    land_points = []
    for x, y, z in sphere_points:
        lat, lon = cartesian_to_latlon(x, y, z)
        if is_land(img, lat, lon, threshold):
            land_points.append({
                "lat": round(lat, 2),
                "lon": round(lon, 2)
            })

    print(f"✓ Found {len(land_points)} land points ({len(land_points)/num_sphere_points*100:.1f}% of sphere)")
    return land_points


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Earth landmass points")
    parser.add_argument("-n", "--num-points", type=int, default=8000,
                        help="Number of Fibonacci sphere points to generate (default: 8000)")
    parser.add_argument("-t", "--threshold", type=int, default=50,
                        help="Brightness threshold for land detection 0-255 (default: 50)")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output JSON file path")
    args = parser.parse_args()

    # Generate points
    land_points = generate_land_points(args.num_points, args.threshold)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent.parent.parent / "short-gravity-web" / "components" / "earth" / "landmass-points.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to JSON
    with open(output_path, 'w') as f:
        json.dump(land_points, f)

    print(f"✓ Saved {len(land_points)} points to {output_path}")

    # Also generate TypeScript version
    ts_path = output_path.with_suffix('.ts')
    ts_content = f"""// Auto-generated landmass points using Fibonacci sphere + land mask
// Generated with {args.num_points} sphere points, threshold {args.threshold}
// Total land points: {len(land_points)}

export interface LandmassPoint {{
  lat: number
  lon: number
}}

export const LANDMASS_POINTS: LandmassPoint[] = {json.dumps(land_points, indent=2)}
"""

    with open(ts_path, 'w') as f:
        f.write(ts_content)

    print(f"✓ Saved TypeScript version to {ts_path}")


if __name__ == "__main__":
    main()
