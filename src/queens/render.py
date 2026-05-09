"""PNG rendering for Queens boards.

Produces a clean, LinkedIn-style board image: coloured regions on a grid,
no queen markers — just the puzzle as a player would see it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .board import Board

# A carefully chosen palette of 20 visually distinct, soft region colours.
# Ordered so adjacent indices don't share similar hues.
_REGION_COLORS: tuple[tuple[int, int, int], ...] = (
    (249, 192, 168),  # peach
    (183, 219, 165),  # sage
    (168, 198, 249),  # sky blue
    (255, 216, 140),  # gold
    (209, 178, 242),  # lavender
    (162, 234, 222),  # mint
    (255, 175, 175),  # salmon
    (188, 213, 178),  # celadon
    (243, 205, 238),  # pink
    (170, 211, 254),  # cornflower
    (255, 236, 153),  # lemon
    (196, 186, 228),  # periwinkle
    (180, 241, 199),  # seafoam
    (255, 194, 194),  # blush
    (175, 205, 240),  # powder blue
    (241, 220, 170),  # cream
    (222, 188, 246),  # mauve
    (172, 237, 207),  # spearmint
    (253, 200, 156),  # apricot
    (179, 197, 250),  # baby blue
)


def render_board_png(
    board: Board,
    path: str | Path,
    *,
    cell_size: int = 64,
) -> None:
    """Render a board as a PNG image without solution markers.

    Produces a clean puzzle image in the LinkedIn Queens style:
    - Each region gets a distinct soft colour.
    - Cells have rounded corners with thin grid gaps.
    - No queens are shown — just the coloured board.

    Args:
        board: The board to render.
        path: Output file path (``.png`` extension).
        cell_size: Pixel size of each cell (default 64).
    """
    n = board.n
    regions = board.regions

    # Layout
    gap = max(2, cell_size // 32)  # grid gap scales with cell size
    radius = max(3, cell_size // 8)  # corner radius
    img_w = n * cell_size + (n + 1) * gap
    img_h = n * cell_size + (n + 1) * gap

    # Build colour map: assign each region ID a colour (cycle palette if n > 20)
    colour_map: dict[int, tuple[int, int, int]] = {}
    for rid in range(n):
        colour_map[rid] = _REGION_COLORS[rid % len(_REGION_COLORS)]

    # Create image with white background
    img = Image.new("RGB", (img_w, img_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    for r in range(n):
        for c in range(n):
            rid = int(regions[r, c])
            fill = colour_map[rid]

            x0 = gap + c * (cell_size + gap)
            y0 = gap + r * (cell_size + gap)
            x1 = x0 + cell_size
            y1 = y0 + cell_size

            # Draw rounded rectangle cell
            draw.rounded_rectangle(
                (x0, y0, x1, y1),
                radius=radius,
                fill=fill,
                outline=None,
            )

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), "PNG")
