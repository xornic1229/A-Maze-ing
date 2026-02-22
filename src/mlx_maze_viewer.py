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


def load_maze_from_file(filename: str) -> list[list[int]]:
    """
    Load a maze from a text file containing hexadecimal values.
    Each hex value (0-F) represents a wall bitmask:
    0=no walls, 1=N, 2=E, 4=S, 8=W, F=all walls, etc.
    """
    matrix = []

    try:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()  # Remove spaces and newlines in the beggining and end of the line
                if not line or line.startswith("#"):  # Goes to the next line if the line is empty or is a comment
                    continue

                # Parse hexadecimal values from the line
                row = []
                for hex_val in line:
                    try:
                        value = int(hex_val, 16)
                        value = value & 0xF
                        row.append(value)
                    except ValueError:
                        row.append(0)

                if row:
                    matrix.append(row)

    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except Exception as e:
        raise Exception(f"Error reading file {filename}: {e}")

    if not matrix:
        raise ValueError(f"No valid maze data found in {filename}")

    return matrix


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
) -> None:
    """
    Fill the window margins with a specified neon color using a 1x1 XPM asset:
    assets/green_margin.xpm, assets/pink_margin.xpm, assets/rainbow_margin.xpm
    """
    margin_path = f"assets/{color}_margin.xpm"
    try:
        result = m.mlx_xpm_file_to_image(mlx_ptr, margin_path)
    except Exception as e:
        raise RuntimeError(f"Error loading margin asset {margin_path}: {e}")

    if not result or not result[0]:
        raise RuntimeError(f"{margin_path} could not be loaded")

    margin_px = result[0]  # expected 1x1 image pointer

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
) -> None:
    """
    Redraw margin + maze using the selected color theme.
    """
    fill_margins_with_background(m, mlx_ptr, window_ptr, window_width, window_height, margin, color)
    draw_maze_tiles(m, mlx_ptr, window_ptr, matrix, assets, margin=margin)


def main() -> None:
    maze_file = MAPA_A_CARGAR

    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() returned NULL")

    matrix = load_maze_from_file(maze_file)

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

    # Start color
    color_index = 0
    current_color = COLOR_CYCLE[color_index]
    assets = assets_by_color[current_color]

    change_color(m, mlx_ptr, win_ptr, matrix, assets, margin, win_width, win_height, current_color)

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