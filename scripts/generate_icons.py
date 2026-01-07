#!/usr/bin/env python3
"""
Generate app icons for LiveRecall
Creates icons for macOS (.icns) and Windows (.ico)
"""

import math
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

# Output directory
ROOT = Path(__file__).parent.parent
ASSETS = ROOT / "assets"

# Icon colors
BG_COLOR = (20, 20, 20, 255)  # Dark background
FG_COLOR = (134, 239, 172, 255)  # Green (#86efac)


def create_app_icon(size: int) -> Image.Image:
    """
    Create the LiveRecall app icon - circular arrow (rewind/recall symbol)
    Returns a high-quality icon at the specified size
    """
    # Create RGBA image with dark background
    img = Image.new("RGBA", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Calculate dimensions
    cx, cy = size // 2, size // 2
    margin = size // 8
    radius = size // 2 - margin
    line_width = max(4, size // 16)

    # Draw circular arc (about 300 degrees, leaving gap for arrow)
    start_angle = 60
    end_angle = 330

    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.arc(bbox, start_angle, end_angle, fill=FG_COLOR, width=line_width)

    # Draw arrowhead at the start of the arc
    arrow_angle_rad = math.radians(start_angle)
    arrow_x = cx + radius * math.cos(arrow_angle_rad)
    arrow_y = cy + radius * math.sin(arrow_angle_rad)

    arrow_size = line_width * 3
    tangent_angle = arrow_angle_rad - math.pi / 2

    tip_x = arrow_x + arrow_size * 0.6 * math.cos(tangent_angle)
    tip_y = arrow_y + arrow_size * 0.6 * math.sin(tangent_angle)

    spread_angle = math.pi / 3
    base1_x = arrow_x + arrow_size * 0.5 * math.cos(tangent_angle + math.pi - spread_angle)
    base1_y = arrow_y + arrow_size * 0.5 * math.sin(tangent_angle + math.pi - spread_angle)
    base2_x = arrow_x + arrow_size * 0.5 * math.cos(tangent_angle + math.pi + spread_angle)
    base2_y = arrow_y + arrow_size * 0.5 * math.sin(tangent_angle + math.pi + spread_angle)

    draw.polygon([(tip_x, tip_y), (base1_x, base1_y), (base2_x, base2_y)], fill=FG_COLOR)

    return img


def create_icns():
    """Create macOS .icns file"""
    print("Creating macOS icon...")

    # Sizes required for icns
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    with tempfile.TemporaryDirectory() as tmpdir:
        iconset = Path(tmpdir) / "icon.iconset"
        iconset.mkdir()

        for size in sizes:
            icon = create_app_icon(size)

            # Standard resolution
            icon.save(iconset / f"icon_{size}x{size}.png")

            # Retina (@2x) - stored as NxN@2x
            if size <= 512:
                icon_2x = create_app_icon(size * 2)
                icon_2x.save(iconset / f"icon_{size}x{size}@2x.png")

        # Convert to icns using iconutil
        icns_path = ASSETS / "icon.icns"
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)], check=True)

        print(f"Created: {icns_path}")


def create_ico():
    """Create Windows .ico file"""
    print("Creating Windows icon...")

    # Sizes for ICO (Windows supports up to 256)
    sizes = [16, 32, 48, 64, 128, 256]

    images = []
    for size in sizes:
        icon = create_app_icon(size)
        images.append(icon)

    # Save as ICO
    ico_path = ASSETS / "icon.ico"
    images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Created: {ico_path}")


def create_png():
    """Create high-res PNG for web/other uses"""
    print("Creating PNG icon...")

    icon = create_app_icon(1024)
    png_path = ASSETS / "icon.png"
    icon.save(png_path, format="PNG")
    print(f"Created: {png_path}")


def main():
    ASSETS.mkdir(exist_ok=True)

    # Create all icon formats
    create_png()
    create_ico()

    # Only create icns on macOS
    import platform

    if platform.system() == "Darwin":
        create_icns()
    else:
        print("Skipping .icns (not on macOS)")

    print("\nDone!")


if __name__ == "__main__":
    main()
