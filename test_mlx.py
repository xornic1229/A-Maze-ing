# test_mlx_assets.py
# Ejecuta: source .venv/bin/activate && python test_mlx_assets.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mlx

# Bitmask walls: 1=N, 2=E, 4=S, 8=W
N, E, S, W = 1, 2, 4, 8


def build_mock_maze(width: int, height: int) -> list[list[int]]:
    """
    Build a small invented maze grid (bitmask per cell) to test rendering with XPM tiles.
    This ensures:
      - outer borders are closed
      - some internal walls exist so you can see different tiles
    """
    grid = [[0 for _ in range(width)] for _ in range(height)]

    # Close outer borders
    for x in range(width):
        grid[0][x] |= N
        grid[height - 1][x] |= S
    for y in range(height):
        grid[y][0] |= W
        grid[y][width - 1] |= E

    # Add a vertical internal wall between x=3 and x=4
    for y in range(1, height - 1):
        if 3 < width and 4 < width:
            grid[y][3] |= E
            grid[y][4] |= W

    # Add a horizontal internal wall between y=2 and y=3
    if 2 < height and 3 < height:
        for x in range(1, width - 1):
            grid[2][x] |= S
            grid[3][x] |= N

    # Add a small "room" / shape on the right
    if width >= 8 and height >= 6:
        # box walls around a 2x2 area (cells (6,2),(7,2),(6,3),(7,3))
        for x in (6, 7):
            grid[2][x] |= N
            grid[3][x] |= S
        for y in (2, 3):
            grid[y][6] |= W
            grid[y][7] |= E

    return grid


@dataclass(frozen=True)
class Assets:
    """Holds MLX image pointers for tiles 0..15."""
    tiles: list[Any]
    tile_w: int
    tile_h: int


def load_tiles(m: mlx.Mlx, mlx_ptr: Any) -> Assets:
    hex_names = "0123456789ABCDEF"
    tiles: list[Any] = []

    for ch in hex_names:
        path = f"assets/{ch}.xpm"
        result = m.mlx_xpm_file_to_image(mlx_ptr, path)
        if not result or not result[0]:
            raise RuntimeError(f"No se pudo cargar el asset: {path}")
        # Extraer solo el puntero de imagen de la tupla
        img_ptr = result[0]
        tiles.append(img_ptr)

    # Sabemos que nuestros tiles son 32x32 (los generamos así)
    return Assets(tiles=tiles, tile_w=32, tile_h=32)


def draw_maze_tiles(
    m: mlx.Mlx,
    mlx_ptr: Any,
    win_ptr: Any,
    grid: list[list[int]],
    assets: Assets,
    margin: int = 10,
) -> None:
    """
    Draw the maze by placing a tile image per cell based on its walls bitmask (0..15).
    """
    h = len(grid)
    w = len(grid[0]) if h else 0

    for y in range(h):
        for x in range(w):
            mask = grid[y][x] & 0xF  # ensure 0..15
            img = assets.tiles[mask]
            px = margin + x * assets.tile_w
            py = margin + y * assets.tile_h
            m.mlx_put_image_to_window(mlx_ptr, win_ptr, img, px, py)


def main() -> None:
    # 1) Create MLX wrapper and initialize context
    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() returned NULL")

    # 2) Build mock grid
    grid = build_mock_maze(width=12, height=9)

    # 3) Load neon XPM tile set (0..F) from ./assets
    assets = load_tiles(m, mlx_ptr)

    # 4) Compute window size from maze + margins
    margin = 20
    win_w = margin * 2 + len(grid[0]) * assets.tile_w
    win_h = margin * 2 + len(grid) * assets.tile_h

    win_ptr = m.mlx_new_window(mlx_ptr, win_w, win_h, "A-Maze-ing (XPM neon tiles)")
    if not win_ptr:
        raise RuntimeError("mlx_new_window() returned NULL")

    # 5) Draw maze using tiles
    draw_maze_tiles(m, mlx_ptr, win_ptr, grid, assets, margin=margin)

    # 6) Close handling (ESC + window close button)
    def key_handler(keycode: int, _param: Any) -> int:
        if keycode == 65307:  # ESC
            m.mlx_loop_exit(mlx_ptr)
        return 0

    m.mlx_key_hook(win_ptr, key_handler, None)

    def close_handler(_param: Any) -> int:
        m.mlx_loop_exit(mlx_ptr)
        return 0

    m.mlx_hook(win_ptr, 17, 0, close_handler, None)

    # 7) Loop
    m.mlx_loop(mlx_ptr)

    # 8) Cleanup (nice-to-have; wrapper has mlx_destroy_image, mlx_destroy_window)
    # Note: some MLX versions require cleanup before exiting loop; keeping it simple for test.


if __name__ == "__main__":
    main()