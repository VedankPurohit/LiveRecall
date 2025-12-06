"""
Programmatic icon generation using PIL
"""
import math
from PIL import Image, ImageDraw
from typing import Tuple

from .config import get_icon_size

# Colors (RGB)
COLOR_WHITE = (255, 255, 255)


def create_app_icon(size: Tuple[int, int] = None) -> Image.Image:
    """
    Create the LiveRecall app icon - circular arrow (rewind/recall symbol)
    High resolution white monochrome design for menu bar
    """
    if size is None:
        size = get_icon_size()

    # Create at 2x resolution for retina, then scale down
    scale = 2
    canvas_size = (size[0] * scale, size[1] * scale)

    img = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    w, h = canvas_size
    cx, cy = w // 2, h // 2  # center
    radius = min(w, h) // 2 - 4  # main radius with padding
    line_width = max(3, w // 11)

    # Draw circular arc (about 300 degrees, leaving gap for arrow)
    # PIL arc uses angles: 0=3 o'clock, 90=6 o'clock, etc.
    start_angle = 60
    end_angle = 330

    # Draw the arc
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.arc(bbox, start_angle, end_angle, fill=COLOR_WHITE + (255,), width=line_width)

    # Draw arrowhead at the start of the arc (pointing counterclockwise)
    # Arrow position at start_angle (60 degrees)
    arrow_angle_rad = math.radians(start_angle)
    arrow_x = cx + radius * math.cos(arrow_angle_rad)
    arrow_y = cy + radius * math.sin(arrow_angle_rad)

    # Arrowhead size
    arrow_size = line_width * 2.5

    # Arrow points inward/counterclockwise direction
    # Tangent at this point points roughly up-left
    tangent_angle = arrow_angle_rad - math.pi / 2  # perpendicular to radius

    # Three points of the arrow triangle
    # Tip of arrow
    tip_x = arrow_x + arrow_size * 0.6 * math.cos(tangent_angle)
    tip_y = arrow_y + arrow_size * 0.6 * math.sin(tangent_angle)

    # Two base points (spread perpendicular to tangent)
    spread_angle = math.pi / 3  # 60 degree spread
    base1_x = arrow_x + arrow_size * 0.5 * math.cos(tangent_angle + math.pi - spread_angle)
    base1_y = arrow_y + arrow_size * 0.5 * math.sin(tangent_angle + math.pi - spread_angle)
    base2_x = arrow_x + arrow_size * 0.5 * math.cos(tangent_angle + math.pi + spread_angle)
    base2_y = arrow_y + arrow_size * 0.5 * math.sin(tangent_angle + math.pi + spread_angle)

    # Draw filled triangle arrowhead
    draw.polygon(
        [(tip_x, tip_y), (base1_x, base1_y), (base2_x, base2_y)],
        fill=COLOR_WHITE + (255,)
    )

    # Scale down to target size with antialiasing
    img = img.resize(size, Image.Resampling.LANCZOS)

    return img


def get_app_icon() -> Image.Image:
    """Get the static app icon for the menu bar"""
    return create_app_icon()
