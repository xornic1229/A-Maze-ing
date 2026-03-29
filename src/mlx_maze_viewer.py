# mlx_maze_viewer.py

from __future__ import annotations
import argparse
from dataclasses import dataclass
import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

# pyright: ignore[reportMissingImports]

if TYPE_CHECKING:
    import mlx
else:
    import mlx  # type: ignore[import-untyped]
from config import read_config

DEFAULT_MAP_PATH = "map/generated_map.txt"
DEFAULT_CONFIG_PATH = "config.txt"

MARGIN = 2  # Margin in pixels around the maze; keeps free space
# around the maze for portal markers and prevents edge glitches.
TILE_SIZE = 32  # Size of each tile in pixels.
COLOR_CYCLE = ["green", "pink", "rainbow"]  # Color themes toggled with 'c'.
# How much the path line is shortened to avoid overlapping the portals.
PORTAL_OUTER_RADIUS = 10
LINE_THICKNESS = 4  # Thickness of the path line in pixels.


@dataclass(frozen=True)
class Assets:
    tiles: list[Any]
    tile_width: int
    tile_height: int


@dataclass
class Game:
    # MLX core objects
    m: mlx.Mlx
    mlx_ptr: Any
    win_ptr: Any

    # Maze data and file path
    matrix: list[list[int]]
    entry: tuple[int, int]
    exit_: tuple[int, int]
    moves: str
    map_path: str

    # Rendering / theme
    assets_by_color: dict[str, Assets]
    color_index: int
    current_color: str
    assets: Assets

    # Window / grid
    tile_size: int
    margin: int
    win_width: int
    win_height: int

    # Pixels
    green_px: Any
    pink_px: Any
    red_px: Any
    black_px: Any

    # Path animation state
    path: list[tuple[int, int]]
    path_progress: int
    animating: bool
    reverse_animating: bool
    last_update: float
    animation_speed: float


def load_maze_from_file(
    filename: str,
) -> tuple[list[list[int]], tuple[int, int], tuple[int, int], str]:
    """Load maze matrix (hex rows) plus entry, exit and moves.

    Returns matrix, entry, exit, and moves string.
    """

    matrix: list[list[int]] = []

    with open(filename, "r") as file:
        lines = [line.strip() for line in file]

    while lines and lines[-1] == "":
        lines.pop()

    moves = lines.pop()
    exit_line = lines.pop()
    entry_line = lines.pop()

    entry_xy = tuple(map(int, entry_line.split(",")))
    exit_xy = tuple(map(int, exit_line.split(",")))

    # The map format stores coordinates as x,y; the viewer works internally
    # as row,col.
    entry = (entry_xy[1], entry_xy[0])
    exit_ = (exit_xy[1], exit_xy[0])

    for line in lines:
        if not line:
            continue
        row: list[int] = []
        for hex_val in line:
            try:
                row.append(int(hex_val, 16) & 0xF)
            except ValueError as exc:
                msg = f"Invalid hexadecimal value '{hex_val}' in maze matrix"
                raise ValueError(msg) from exc
        matrix.append(row)

    if not matrix:
        raise ValueError("Maze file is empty or missing matrix data")

    return matrix, entry, exit_, moves


def load_tiles(m: mlx.Mlx, mlx_ptr: Any, color: str) -> Assets:
    """Load tile images for a given color theme.

    Expects 'assets/<color>/0.xpm' .. 'F.xpm'.
    """

    hex_names = "0123456789ABCDEF"
    tiles: list[Any] = []

    for ch in hex_names:
        path = f"assets/{color}/{ch}.xpm"
        result = m.mlx_xpm_file_to_image(mlx_ptr, path)
        if not result or not result[0]:
            raise RuntimeError(f"Asset {ch} could not be loaded from {path}")
        tiles.append(result[0])

    return Assets(tiles=tiles, tile_width=TILE_SIZE, tile_height=TILE_SIZE)


def load_pixel(m: mlx.Mlx, mlx_ptr: Any, path: str) -> Any:
    res = m.mlx_xpm_file_to_image(mlx_ptr, path)
    if not res or not res[0]:
        raise RuntimeError(f"Pixel asset could not be loaded: {path}")
    return res[0]


def build_path_from_moves(
    entry: tuple[int, int],
    moves: str,
) -> list[tuple[int, int]]:
    """Build a list of path cells from an entry point and move string.

    Moves use chars 'N', 'S', 'E', 'W'.
    """

    row, col = entry
    path = [(row, col)]

    for move in moves:
        if move == "N":
            row -= 1
        elif move == "S":
            row += 1
        elif move == "E":
            col += 1
        elif move == "W":
            col -= 1
        else:
            continue
        path.append((row, col))

    return path


def cell_center_px(game: Game, pos: tuple[int, int]) -> tuple[int, int]:
    """Convert grid coordinates to pixel coordinates of the cell center."""
    r, c = pos
    x = game.margin + c * game.tile_size + game.tile_size // 2
    y = game.margin + r * game.tile_size + game.tile_size // 2
    return x, y


def offset_point_towards(
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    offset: int,
) -> tuple[int, int]:
    """Calculate a point offset pixels away from (x0, y0) towards (x1, y1)."""
    dx = x1 - x0
    dy = y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return x0, y0

    nx = dx / length
    ny = dy / length
    return int(x0 + nx * offset), int(y0 + ny * offset)


def draw_line_bresenham(
    game: Game,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    pixel_img: Any,
    thickness: int = 1,
) -> None:
    """Draw a line with Bresenham's algorithm (optionally thicker than 1px)."""
    m = game.m

    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        if thickness <= 1:
            m.mlx_put_image_to_window(
                game.mlx_ptr,
                game.win_ptr,
                pixel_img,
                x0,
                y0,
            )
        else:
            t = thickness // 2
            for oy in range(-t, t + 1):
                for ox in range(-t, t + 1):
                    m.mlx_put_image_to_window(
                        game.mlx_ptr,
                        game.win_ptr,
                        pixel_img,
                        x0 + ox,
                        y0 + oy,
                    )

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_path_segment(
    game: Game,
    a: tuple[int, int],
    b: tuple[int, int],
    index: int,
    pixel_img: Any,
) -> None:
    """Draw a segment of the path from cell 'a' to 'b'."""
    ax, ay = cell_center_px(game, a)
    bx, by = cell_center_px(game, b)

    if index == 1:
        ax, ay = offset_point_towards(
            ax,
            ay,
            bx,
            by,
            PORTAL_OUTER_RADIUS + 2,
        )

    if index == len(game.path) - 1:
        bx, by = offset_point_towards(
            bx,
            by,
            ax,
            ay,
            PORTAL_OUTER_RADIUS + 2,
        )

    draw_line_bresenham(
        game,
        ax,
        ay,
        bx,
        by,
        pixel_img=pixel_img,
        thickness=LINE_THICKNESS,
    )


def fill_margins_with_background(game: Game) -> None:
    """Fill the margins around the maze with the matching background."""

    m = game.m
    color = game.current_color
    margin_path = f"assets/{color}_margin.xpm"
    margin_px = load_pixel(m, game.mlx_ptr, margin_path)

    for y in range(game.margin):
        for x in range(game.win_width):
            m.mlx_put_image_to_window(
                game.mlx_ptr,
                game.win_ptr,
                margin_px,
                x,
                y,
            )
            m.mlx_put_image_to_window(
                game.mlx_ptr,
                game.win_ptr,
                margin_px,
                x,
                game.win_height - 1 - y,
            )

    for x in range(game.margin):
        for y in range(game.win_height):
            m.mlx_put_image_to_window(
                game.mlx_ptr,
                game.win_ptr,
                margin_px,
                x,
                y,
            )
            m.mlx_put_image_to_window(
                game.mlx_ptr,
                game.win_ptr,
                margin_px,
                game.win_width - 1 - x,
                y,
            )


def draw_maze_tiles(game: Game) -> None:
    """Draw the maze tiles based on the matrix data."""
    m = game.m
    game.path_progress = 0
    if not game.animating and not game.reverse_animating:
        for r in range(len(game.matrix)):
            for c in range(len(game.matrix[r])):
                val = game.matrix[r][c] & 0xF
                tile = game.assets.tiles[val]
                x = game.margin + c * game.tile_size
                y = game.margin + r * game.tile_size
                m.mlx_put_image_to_window(
                    game.mlx_ptr,
                    game.win_ptr,
                    tile,
                    x,
                    y,
                )


def draw_portal_marker(
    game: Game,
    pos: tuple[int, int],
    pixel_img: Any,
) -> None:
    """Draw a circular marker around the portal entry/exit."""
    m = game.m
    row, col = pos

    cx = (
        game.margin
        + col * game.tile_size
        + game.tile_size // 2
    )
    cy = (
        game.margin
        + row * game.tile_size
        + game.tile_size // 2
    )

    outer_r = PORTAL_OUTER_RADIUS
    inner_r = 7
    outer2 = outer_r * outer_r
    inner2 = inner_r * inner_r

    for dy in range(-outer_r, outer_r + 1):
        for dx in range(-outer_r, outer_r + 1):
            d2 = dx * dx + dy * dy
            if inner2 <= d2 <= outer2:
                m.mlx_put_image_to_window(
                    game.mlx_ptr,
                    game.win_ptr,
                    pixel_img,
                    cx + dx,
                    cy + dy,
                )


def draw_path_upto(game: Game, progress_points: int) -> None:
    """Draw the path segments up to the given progress point index."""
    if progress_points <= 1:
        return
    for i in range(1, progress_points):
        draw_path_segment(
            game,
            game.path[i - 1],
            game.path[i],
            i,
            pixel_img=game.red_px,
        )


def redraw_all(game: Game) -> None:
    """Redraw margins, maze tiles, current path and portal markers."""
    fill_margins_with_background(game)
    draw_maze_tiles(game)
    draw_path_upto(game, game.path_progress)
    draw_portal_marker(game, game.entry, game.green_px)
    draw_portal_marker(game, game.exit_, game.pink_px)


def reload_maze_from_disk(game: Game) -> None:
    """Reload maze state from disk and redraw current scene."""
    matrix, entry, exit_, moves = load_maze_from_file(game.map_path)
    game.matrix = matrix
    game.entry = entry
    game.exit_ = exit_
    game.moves = moves
    game.path = build_path_from_moves(entry, moves)
    game.path_progress = 0
    game.animating = False
    game.reverse_animating = False
    redraw_all(game)


def regenerate_and_reload(game: Game) -> None:
    """Generate a fresh maze from config.txt and display it."""
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    config_path = os.path.join(project_root, DEFAULT_CONFIG_PATH)
    entrypoint_path = os.path.join(project_root, "a_maze_ing.py")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config file not found: {config_path}")
    if not os.path.exists(entrypoint_path):
        raise FileNotFoundError(f"entrypoint not found: {entrypoint_path}")

    result = subprocess.run(
        [sys.executable, entrypoint_path, config_path],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        command_output = (
            result.stderr.strip()
            or result.stdout.strip()
            or "unknown error"
        )
        raise RuntimeError(f"maze regeneration failed: {command_output}")

    config = read_config(config_path)
    generated_map_path = config.output_file
    if not os.path.isabs(generated_map_path):
        generated_map_path = os.path.join(project_root, generated_map_path)

    game.map_path = generated_map_path
    reload_maze_from_disk(game)


def key_handler(keycode: int, game: Game) -> int:
    """Handle key presses for quit/theme/regenerate and path animation."""
    if keycode == 65307:  # ESC
        game.m.mlx_loop_exit(game.mlx_ptr)
        return 0

    if keycode == 99:  # 'c'
        game.color_index = (game.color_index + 1) % len(COLOR_CYCLE)
        game.current_color = COLOR_CYCLE[game.color_index]
        game.assets = game.assets_by_color[game.current_color]
        redraw_all(game)
        return 0

    if keycode == 110:  # 'n'
        try:
            regenerate_and_reload(game)
            print(f"Generated and loaded new maze from {game.map_path}")
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Could not generate a new maze: {exc}")
        return 0

    if keycode == 115:  # 's'
        # If any animation is running, ignore
        if game.animating or game.reverse_animating:
            return 0

        # If the path is fully drawn, start reverse erase from exit to entry
        if game.path_progress >= len(game.path):
            game.reverse_animating = True
            game.last_update = time.time()
            return 0

        # Otherwise start forward draw
        game.animating = True
        game.last_update = time.time()
        return 0

    return 0


def loop_hook(game: Game) -> int:
    """Loop hook to handle path animation (draw forward / erase backward)."""
    now = time.time()

    if not game.animating and not game.reverse_animating:
        return 0

    if now - game.last_update < game.animation_speed:
        return 0

    game.last_update = now

    # Forward (red) animation
    if game.animating:
        if game.path_progress < len(game.path):
            if game.path_progress == 0:
                game.path_progress = 1
            else:
                i = game.path_progress
                draw_path_segment(
                    game,
                    game.path[i - 1],
                    game.path[i],
                    i,
                    pixel_img=game.red_px,
                )
                game.path_progress += 1
        else:
            game.animating = False
        return 0

    # Reverse (black) animation - erase from exit to entry
    if game.reverse_animating:
        # path_progress is the "end" index visible; erase segment
        # (path_progress-2 -> path_progress-1)
        if game.path_progress > 1:
            i = game.path_progress - 1
            draw_path_segment(
                game,
                game.path[i - 1],
                game.path[i],
                i,
                pixel_img=game.black_px,
            )
            game.path_progress -= 1
        else:
            game.reverse_animating = False

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="MLX maze viewer")
    parser.add_argument("map_file", nargs="?", default=DEFAULT_MAP_PATH)
    args = parser.parse_args()

    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() failed")

    map_path = os.path.abspath(args.map_file)
    matrix, entry, exit_, moves = load_maze_from_file(map_path)

    max_cols = max(len(r) for r in matrix)
    win_width = MARGIN * 2 + max_cols * TILE_SIZE
    win_height = MARGIN * 2 + len(matrix) * TILE_SIZE

    win_ptr = m.mlx_new_window(
        mlx_ptr,
        win_width,
        win_height,
        "A-Maze-ing",
    )
    if not win_ptr:
        raise RuntimeError("mlx_new_window() failed")

    assets_by_color = {
        "green": load_tiles(m, mlx_ptr, "green"),
        "pink": load_tiles(m, mlx_ptr, "pink"),
        "rainbow": load_tiles(m, mlx_ptr, "rainbow"),
    }

    green_px = load_pixel(m, mlx_ptr, "assets/green_margin.xpm")
    pink_px = load_pixel(m, mlx_ptr, "assets/pink_margin.xpm")
    red_px = load_pixel(m, mlx_ptr, "assets/red_pixel.xpm")
    black_px = load_pixel(m, mlx_ptr, "assets/black_pixel.xpm")

    color_index = 0
    current_color = COLOR_CYCLE[color_index]
    assets = assets_by_color[current_color]

    path = build_path_from_moves(entry, moves)

    game = Game(
        m=m,
        mlx_ptr=mlx_ptr,
        win_ptr=win_ptr,

        matrix=matrix,
        entry=entry,
        exit_=exit_,
        moves=moves,
        map_path=map_path,

        assets_by_color=assets_by_color,
        color_index=color_index,
        current_color=current_color,
        assets=assets,

        tile_size=TILE_SIZE,
        margin=MARGIN,
        win_width=win_width,
        win_height=win_height,

        green_px=green_px,
        pink_px=pink_px,
        red_px=red_px,
        black_px=black_px,

        path=path,
        path_progress=0,
        animating=False,
        reverse_animating=False,
        last_update=0.0,
        animation_speed=0.01,
    )

    redraw_all(game)

    m.mlx_key_hook(win_ptr, key_handler, game)
    m.mlx_hook(
        win_ptr,
        17,
        0,
        lambda _p: (m.mlx_loop_exit(mlx_ptr), 0)[1],
        None,
    )
    m.mlx_loop_hook(mlx_ptr, loop_hook, game)

    m.mlx_loop(mlx_ptr)


if __name__ == "__main__":
    main()
