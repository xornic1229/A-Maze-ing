# mlx_maze_viewer.py
#
# This module is responsible for rendering a maze on screen using MLX.
# 
# Responsibilities:
# - Load a maze from a hexadecimal text file
# - Load tile assets (0..F) corresponding to wall bitmasks
# - Create and manage the MLX window
# - Render the maze grid visually
# - Handle basic window events (ESC key, window close)
#
# The maze logic (generation/solving) is NOT handled here.
# This file is strictly responsible for visualization.
# For testing it use source .venv/bin/activate and then run python src/mlx_maze_viewer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import os
import mlx

MAPA_A_CARGAR = "mapas_prueba/mapa_masivo.txt"  # Aqui se cargara el mapa que se genere en el generador de mapas

MARGIN = 2

# Cycle order when pressing 'c'
COLOR_CYCLE = ["green", "pink", "rainbow"]


@dataclass(frozen=True)  # Immutable dataclass to hold loaded assets
class Assets:
    """Holds MLX image pointers for tiles."""
    tiles: list[Any]
    tile_width: int
    tile_height: int


def load_maze_from_file(filename: str):
    """
    Returns:
        matrix: list[list[int]]
        entry: (row, col)
        exit: (row, col)
    """

    matrix = []
    entry = None
    exit_ = None

    try:
        with open(filename, "r") as file:
            lines = [line.strip() for line in file]

        # Remove empty trailing lines
        while lines and lines[-1] == "":
            lines.pop()

        # Last two lines are entry and exit
        exit_line = lines.pop()
        entry_line = lines.pop()

        # Parse entry and exit
        entry = tuple(map(int, entry_line.split(",")))
        exit_ = tuple(map(int, exit_line.split(",")))

        # Remaining lines are maze
        for line in lines:
            if not line:
                continue

            row = []
            for hex_val in line:
                try:
                    value = int(hex_val, 16) & 0xF
                    row.append(value)
                except ValueError:
                    row.append(0)

            matrix.append(row)

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except Exception as e:
        raise Exception(f"Error reading file {filename}: {e}")

    if not matrix:
        raise ValueError("Maze data is empty")

    return matrix, entry, exit_


def load_tiles(m: mlx.Mlx, mlx_ptr: Any, color: str) -> Assets:
    """
    Load tiles and return them.
    """
    hex_names = "0123456789ABCDEF"
    tiles: list[Any] = []  # List to hold MLX image pointers for each tile (0..F)

    for ch in hex_names:
        path = f"assets/{color}/{ch}.xpm"
        try:
            result = m.mlx_xpm_file_to_image(mlx_ptr, path)
        except Exception as e:
            raise RuntimeError(f"Error loading asset {ch} from {path}: {e}")

        if not result or not result[0]:
            raise RuntimeError(f"Asset {ch} could not be loaded from {path}")

        tiles.append(result[0])

    # All tiles are assumed to be 32x32 pixels
    base_size = 32
    return Assets(tiles=tiles, tile_width=base_size, tile_height=base_size)


def fill_margins_with_background(
    m: mlx.Mlx,
    mlx_ptr: Any,
    window_ptr: Any,
    window_width: int,
    window_height: int,
    margin: int,
    color: str,
) -> Any:
    """
    Fill the window margins with a specified neon color using a 1x1 XPM asset:
    assets/green_margin.xpm, assets/pink_margin.xpm, assets/rainbow_margin.xpm

    Returns:
        margin_px: 1x1 image pointer used for drawing the margin (can be reused elsewhere).
    """
    margin_path = f"assets/{color}_margin.xpm"
    try:
        result = m.mlx_xpm_file_to_image(mlx_ptr, margin_path)
    except Exception as e:
        raise RuntimeError(f"Error loading margin asset {margin_path}: {e}")

    if not result or not result[0]:
        raise RuntimeError(f"{margin_path} could not be loaded")

    margin_px = result[0]  # 1x1 image pointer

    # Top + Bottom
    for y in range(margin):
        for x in range(window_width):
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, x, y)
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, x, window_height - 1 - y)

    # Left + Right
    for x in range(margin):
        for y in range(window_height):
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, x, y)
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, window_width - 1 - x, y)

    return margin_px


def draw_maze_tiles(
    m: mlx.Mlx,
    mlx_ptr: Any,
    window_ptr: Any,
    matrix: list[list[int]],
    assets: Assets,
    margin: int,
) -> None:
    """
    Draw the maze (matrix) using the 16 preloaded tiles (assets.tiles[0..15]).
    """
    rows = len(matrix)

    for row in range(rows):
        cols = len(matrix[row])
        for col in range(cols):
            cell_value = matrix[row][col] & 0xF
            tile_image = assets.tiles[cell_value]

            draw_x = margin + col * assets.tile_width
            draw_y = margin + row * assets.tile_height

            m.mlx_put_image_to_window(mlx_ptr, window_ptr, tile_image, draw_x, draw_y)


def draw_portal_marker(
    m: mlx.Mlx,
    mlx_ptr: Any,
    win_ptr: Any,
    position: tuple[int, int],
    margin: int,
    tile_size: int,
    pixel_img: Any,  # 1x1 XPM image pointer
) -> None:
    """
    Draw a neon portal ring inside a cell using a 1x1 pixel image.
    No transparency needed. Does not cover the maze.
    """

    row, col = position

    # Cell center in window pixels
    cx = margin + col * tile_size + tile_size // 2
    cy = margin + row * tile_size + tile_size // 2

    # Portal ring parameters (tweak these)
    outer_r = 10
    inner_r = 7

    outer2 = outer_r * outer_r
    inner2 = inner_r * inner_r

    # Draw ring: points where inner_r^2 <= dx^2+dy^2 <= outer_r^2
    for dy in range(-outer_r, outer_r + 1):
        for dx in range(-outer_r, outer_r + 1):
            d2 = dx * dx + dy * dy
            if inner2 <= d2 <= outer2:
                # Jagged effect
                if (dx * dx + dy * 3) % 7 != 0:
                    m.mlx_put_image_to_window(mlx_ptr, win_ptr, pixel_img, cx + dx, cy + dy)


def change_color(
    m: mlx.Mlx,
    mlx_ptr: Any,
    window_ptr: Any,
    matrix: list[list[int]],
    assets: Assets,
    margin: int,
    window_width: int,
    window_height: int,
    color: str,
) -> Any:
    """
    Redraw margin + maze using the selected color theme.
    Returns:
        margin_px (1x1 image pointer) used for that margin color.
    """
    margin_px = fill_margins_with_background(m, mlx_ptr, window_ptr, window_width, window_height, margin, color)
    draw_maze_tiles(m, mlx_ptr, window_ptr, matrix, assets, margin=margin)
    return margin_px


def main() -> None:
    maze_file = MAPA_A_CARGAR

    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() returned NULL")

    matrix, entry, exit_ = load_maze_from_file(maze_file)

    margin = MARGIN
    max_cols = max(len(r) for r in matrix)
    win_width = margin * 2 + max_cols * 32
    win_height = margin * 2 + len(matrix) * 32

    window_title = f"A-Maze-ing: {os.path.basename(maze_file)} ({max_cols}x{len(matrix)})"
    win_ptr = m.mlx_new_window(mlx_ptr, win_width, win_height, window_title)
    if not win_ptr:
        raise RuntimeError("mlx_new_window() returned NULL")

    # Preload all tile sets so switching is instant
    assets_by_color = {
        "green": load_tiles(m, mlx_ptr, "green"),
        "pink": load_tiles(m, mlx_ptr, "pink"),
        "rainbow": load_tiles(m, mlx_ptr, "rainbow"),
    }

    # Preload 1x1 pixels for portals (these exist already because you use them for margins)
    green_px_res = m.mlx_xpm_file_to_image(mlx_ptr, "assets/green_margin.xpm")
    pink_px_res = m.mlx_xpm_file_to_image(mlx_ptr, "assets/pink_margin.xpm")
    if not green_px_res or not green_px_res[0]:
        raise RuntimeError("assets/green_margin.xpm could not be loaded")
    if not pink_px_res or not pink_px_res[0]:
        raise RuntimeError("assets/pink_margin.xpm could not be loaded")
    green_px = green_px_res[0]
    pink_px = pink_px_res[0]

    # Start color
    color_index = 0
    current_color = COLOR_CYCLE[color_index]
    assets = assets_by_color[current_color]

    # First draw
    change_color(m, mlx_ptr, win_ptr, matrix, assets, margin, win_width, win_height, current_color)
    draw_portal_marker(m, mlx_ptr, win_ptr, entry, margin, 32, green_px)
    draw_portal_marker(m, mlx_ptr, win_ptr, exit_, margin, 32, pink_px)

    def key_handler(keycode: int, _param: Any) -> int:
        nonlocal color_index, current_color, assets

        if keycode == 65307:  # ESC
            m.mlx_loop_exit(mlx_ptr)
            return 0

        if keycode == 99:  # 'c'
            color_index = (color_index + 1) % len(COLOR_CYCLE)
            current_color = COLOR_CYCLE[color_index]
            assets = assets_by_color[current_color]

            change_color(m, mlx_ptr, win_ptr, matrix, assets, margin, win_width, win_height, current_color)

            # Re-draw portals on top after redraw
            draw_portal_marker(m, mlx_ptr, win_ptr, entry, margin, 32, green_px)
            draw_portal_marker(m, mlx_ptr, win_ptr, exit_, margin, 32, pink_px)
            return 0

        return 0

    m.mlx_key_hook(win_ptr, key_handler, None)

    def close_handler(_param: Any) -> int:
        m.mlx_loop_exit(mlx_ptr)
        return 0

    m.mlx_hook(win_ptr, 17, 0, close_handler, None)

    m.mlx_loop(mlx_ptr)


if __name__ == "__main__":
    main()