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

MAPA_A_CARGAR = "mapas_prueba/map1.txt"  # Aqui se cargara el mapa que se genere en el generador de mapas

@dataclass(frozen=True) # Immutable dataclass to hold loaded assets
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
        with open(filename, 'r') as file:
            for line in file:
                line = line.strip() # Remove spaces and newlines in the beggining and end of the line
                if not line or line.startswith('#'):  # Goes to the next line if the line is empty or is a comment
                    continue
                
                # Parse hexadecimal values from the line
                row = []
                for hex_val in line:
                    try:
                        # Convert hex string to integer
                        value = int(hex_val, 16)
                        # Ensure value is in valid range (0-15)
                        value = value & 0xF
                        row.append(value)
                    except ValueError:
                        # If not a valid hex value, treat as 0 (no walls)
                        row.append(0)
                
                if row:  # Only add non-empty rows
                    matrix.append(row)
                    
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except Exception as e:
        raise Exception(f"Error reading file {filename}: {e}")
    
    if not matrix:
        # If no valid data found, return a default maze
        raise ValueError(f"No valid maze data found in {filename}")
    
    return matrix


def load_tiles(m: mlx.Mlx, mlx_ptr: Any) -> Assets:
    """
    Load tiles and return them.
    """
    hex_names = "0123456789ABCDEF"
    tiles: list[Any] = [] # List to hold MLX image pointers for each tile (0..F)

    for ch in hex_names: # Loads and stores the image pointer into the list
        try:
            path = f"assets/{ch}.xpm"
            result = m.mlx_xpm_file_to_image(mlx_ptr, path)
        except Exception as e:
            raise RuntimeError(f"Error loading asset {ch}: {e}")

        if not result or not result[0]:
            raise RuntimeError(f"Asset {ch} could not be loaded from {path}")

        img_ptr = result[0]
        tiles.append(img_ptr)

    # All tiles are assumed to be 32x32 pixels
    base_size = 32
    return Assets(tiles = tiles, tile_width=base_size, tile_height=base_size)

def fill_margins_with_background( m: mlx.Mlx, mlx_ptr: Any, window_ptr: Any,
    window_width: int, window_height: int, margin: int) -> None:
    """
    Fill the window margins with green neon color using a green XPM asset.
    """
    try:
        result = m.mlx_xpm_file_to_image(mlx_ptr, "assets/green_margin.xpm")
        if not result or not result[0]:
            raise RuntimeError("green_margin.xpm could not be loaded")

        green_img = result[0]

        # If the wrapper returns width/height, use them; otherwise assume 32x32
        tile_w = result[1] if len(result) > 1 and isinstance(result[1], int) else 32
        tile_h = result[2] if len(result) > 2 and isinstance(result[2], int) else 32

        # Top margin
        for y in range(0, margin, tile_h):
            for x in range(0, window_width, tile_w):
                m.mlx_put_image_to_window(mlx_ptr, window_ptr, green_img, x, y)

        # Bottom margin
        for y in range(window_height - margin, window_height, tile_h):
            for x in range(0, window_width, tile_w):
                m.mlx_put_image_to_window(mlx_ptr, window_ptr, green_img, x, y)

        # Left margin (excluding corners already filled)
        for y in range(margin, window_height - margin, tile_h):
            for x in range(0, margin, tile_w):
                m.mlx_put_image_to_window(mlx_ptr, window_ptr, green_img, x, y)

        # Right margin (excluding corners already filled)
        for y in range(margin, window_height - margin, tile_h):
            for x in range(window_width - margin, window_width, tile_w):
                m.mlx_put_image_to_window(mlx_ptr, window_ptr, green_img, x, y)

    except Exception as e:
        raise RuntimeError(f"Error creating green margin: {e}")

def draw_maze_tiles(m: mlx.Mlx,mlx_ptr: Any,window_ptr: Any,matrix: list[list[int]],
assets: Assets,margin: int) -> None:
    """
    Draw the maze (matrix) using the 16 preloaded tiles (assets.tiles[0..15]).

    Each matrix cell stores a wall bitmask encoded as a hex digit (0..F), i.e. an int in 0..15.
    We use that value to pick the corresponding sprite: assets.tiles[cell_value].

    """

    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0

    for row in range(rows):
        for col in range(cols):
            # 1) Read the cell encoded value (0..15). This represents which walls are present.
            cell_value = matrix[row][col] & 0xF

            # 2) Pick the correct sprite for this cell.
            tile_image = assets.tiles[cell_value]

            # 3) Compute the top-left pixel of this cell on the window.
            draw_x = margin + col * assets.tile_width
            draw_y = margin + row * assets.tile_height

            # 4) Draw the tile once (no fake scaling).
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, tile_image, draw_x, draw_y)


def main() -> None:
    # 1) Use configured map file
    maze_file = MAPA_A_CARGAR    
    # 2) Create MLX wrapper and initialize context
    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() returned NULL")

    # 3) Load maze from selected file
    matrix = load_maze_from_file(maze_file)
    
    # 4) Load neon XPM tile set (0..F) from ./assets
    assets = load_tiles(m, mlx_ptr)
    # 5) Compute window size from maze + margins
    margin = 2  # Increased margin for better visibility of green color
    win_width = margin * 2 + len(matrix[0]) * assets.tile_width
    win_height = margin * 2 + len(matrix) * assets.tile_height

    window_title = f"A-Maze-ing: {os.path.basename(maze_file)} ({len(matrix[0])}x{len(matrix)})"
    win_ptr = m.mlx_new_window(mlx_ptr, win_width, win_height, window_title)
    if not win_ptr:
        raise RuntimeError("mlx_new_window() returned NULL")

    # 6) Fill margins with green neon color #39FF14
    fill_margins_with_background(m, mlx_ptr, win_ptr, win_width, win_height, margin)

    # 7) Draw maze using scaled tiles
    draw_maze_tiles(m, mlx_ptr, win_ptr, matrix, assets, margin=margin)

    # 8) Close handling (ESC + window close button)
    def key_handler(keycode: int, _param: Any) -> int:
        if keycode == 65307:  # ESC
            m.mlx_loop_exit(mlx_ptr)
            return 0
        return 0

    m.mlx_key_hook(win_ptr, key_handler, None)

    def close_handler(_param: Any) -> int:
        m.mlx_loop_exit(mlx_ptr)
        return 0

    m.mlx_hook(win_ptr, 17, 0, close_handler, None)

    # 9) Loop
    m.mlx_loop(mlx_ptr)

if __name__ == "__main__":
    main()