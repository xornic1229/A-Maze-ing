# mlx_maze_viewer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import time
import mlx # pyright: ignore[reportMissingImports]

MAPA_A_CARGAR = "mapas_prueba/mapa_masivo.txt"  # Change this to load different mazes

MARGIN = 2 # Margin in pixels around the maze, used to create a border and space for portal markers, also helps prevent drawing issues at the edges of the window
TILE_SIZE = 32 # Size of each tile in pixels, used for calculating window size and drawing positions
COLOR_CYCLE = ["green", "pink", "rainbow"] # List of color themes to cycle through when pressing 'c'
PORTAL_OUTER_RADIUS = 10   # This radius determines how much the path line is shortened at the start and end to avoid overlapping the portal markers
LINE_THICKNESS = 4 # Thickness of the path line in pixels

@dataclass(frozen=True)
class Assets:
    tiles: list[Any] # List of tile images indexed by the hexadecimal value from the maze matrix
    tile_width: int # Width of each tile in pixels
    tile_height: int # Height of each tile in pixels


@dataclass
class Game:
    # MLX
    m: mlx.Mlx # Reference to the MLX instance for calling MLX functions
    mlx_ptr: Any # Pointer returned by mlx_init(), needed for all MLX calls
    win_ptr: Any # Pointer to the created window, needed for drawing and event handling

    # Maze
    matrix: list[list[int]] # 2D list representing the maze structure, where each cell's value determines which tile to draw
    entry: tuple[int, int] # Coordinates of the maze entry point (row, column)
    exit_: tuple[int, int] # Coordinates of the maze exit point (row, column)
    moves: str # String of moves (N, S, E, W) that represents the path through the maze from entry to exit, used for animation

    # Rendering / theme
    assets_by_color: dict[str, Assets] # Dictionary mapping color themes to their corresponding loaded assets, allowing for easy switching of themes
    color_index: int # Index to track the current color theme in the COLOR_CYCLE list
    current_color: str # The current color theme being used, which determines which set of tile images to draw and which margin color to use
    assets: Assets # The currently active set of assets (tiles) based on the selected color theme, used for drawing the maze tiles

    # Window / grid
    tile_size: int # Size of each tile in pixels
    margin: int # Margin around the maze in pixels
    win_width: int # Width of the window in pixels
    win_height: int # Height of the window in pixels

    # Pixels
    green_px: Any # Pixel image used for drawing the green portal marker (entry)
    pink_px: Any # Pixel image used for drawing the pink portal marker (exit)
    red_px: Any # Pixel image used for drawing the path line (red)

    # Path animation state
    path: list[tuple[int, int]] # List of coordinates representing the full path through the maze, built from the entry point and moves string
    path_progress: int # Index into the path list indicating how many segments of the path have been drawn so far, used for animating the path drawing
    animating: bool # Flag to indicate whether the path animation is currently active, preventing multiple simultaneous animations and controlling the flow of the animation in the loop hook
    last_update: float # Timestamp of the last update during animation, used to control the animation speed by ensuring updates only happen after a certain time interval has passed
    animation_speed: float # Time in seconds between animation updates, controlling how fast the path is drawn during animation (e.g., 0.01 for 10ms per segment)

def load_maze_from_file(filename: str) -> tuple[list[list[int]], tuple[int, int], tuple[int, int], str]:
    """Read maze data in from the selected map with the first lines as the maze matrix in hexadecimal,
    and the last 3 lines as entry, exit, and moves. It returns the matrix as a list of lists of integers, 
    the entry and exit as coordinate tuples, and the moves as a string."""

    matrix: list[list[int]] = [] # Matrix to hold the map tiles as integrers

    with open(filename, "r") as file:
        lines = [line.strip() for line in file]

    while lines and lines[-1] == "":
        lines.pop()

    moves = lines.pop()
    exit_line = lines.pop()
    entry_line = lines.pop()

    entry = tuple(map(int, entry_line.split(",")))
    exit_ = tuple(map(int, exit_line.split(",")))

    for line in lines:
        if not line:
            continue
        row: list[int] = []
        for hex_val in line:
            try:
                row.append(int(hex_val, 16) & 0xF)
            except ValueError as e:
                raise ValueError(f"Invalid hexadecimal value '{hex_val}' in maze matrix with error: {e}")
        matrix.append(row)

    if not matrix:
        raise ValueError("Maze file is empty or does not contain a valid matrix")

    return matrix, entry, exit_, moves

def load_tiles(m: mlx.Mlx, mlx_ptr: Any, color: str) -> Assets:
    """Load tile images for a given color theme and it returns an Assets object containing the list 
    of tile images and their dimensions. It expects the tile images to be named as '0.xpm', '1.xpm', ..., 'F.xpm' 
    in the corresponding color folder under assets (e.g., 'assets/green/0.xpm')."""

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


def build_path_from_moves(entry: tuple[int, int], moves: str) -> list[tuple[int, int]]:
    """Given an entry point and a string of moves, build the full path as a list of the coordinates of the 
    cells that will form the path. The moves string consists of characters 'N', 'S', 'E', 'W' representing 
    the direction of movement from one cell to the next."""

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


def offset_point_towards(x0: int, y0: int, x1: int, y1: int, offset: int) -> tuple[int, int]:
    """Calculate a point that is 'offset' pixels away from (x0, y0) towards (x1, y1)."""
    dx = x1 - x0
    dy = y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return x0, y0

    nx = dx / length
    ny = dy / length
    return int(x0 + nx * offset), int(y0 + ny * offset)


def draw_line_bresenham(game: Game, x0: int, y0: int, x1: int, y1: int, thickness: int = 1) -> None:
    """Draw a line from (x0, y0) to (x1, y1) using Bresenham's algorithm, with optional thickness."""
    m = game.m

    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        if thickness <= 1:
            m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, game.red_px, x0, y0)
        else:
            t = thickness // 2
            for oy in range(-t, t + 1):
                for ox in range(-t, t + 1):
                    m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, game.red_px, x0 + ox, y0 + oy)

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_path_segment(game: Game, a: tuple[int, int], b: tuple[int, int], index: int) -> None:
    """Draw a segment of the path from cell 'a' to cell 'b', with adjustments for portal entry/exit."""
    ax, ay = cell_center_px(game, a)
    bx, by = cell_center_px(game, b)

    # First segment: shortened to avoid overlapping the portal entry marker
    if index == 1:
        ax, ay = offset_point_towards(ax, ay, bx, by, PORTAL_OUTER_RADIUS+2)

    # Last segment: shortened to avoid overlapping the portal exit marker
    if index == len(game.path) - 1:
        bx, by = offset_point_towards(bx, by, ax, ay, PORTAL_OUTER_RADIUS+2)

    draw_line_bresenham(game, ax, ay, bx, by, thickness=LINE_THICKNESS)


def fill_margins_with_background(game: Game) -> None:
    """Fill the margins around the maze with the appropriate background color for having the same
    thickness in the exterior wall and the other walls."""

    m = game.m
    color = game.current_color
    margin_path = f"assets/{color}_margin.xpm"
    margin_px = load_pixel(m, game.mlx_ptr, margin_path)

    for y in range(game.margin):
        for x in range(game.win_width):
            m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, margin_px, x, y)
            m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, margin_px, x, game.win_height - 1 - y)

    for x in range(game.margin):
        for y in range(game.win_height):
            m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, margin_px, x, y)
            m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, margin_px, game.win_width - 1 - x, y)


def draw_maze_tiles(game: Game) -> None:
    """Draw the maze tiles based on the matrix data."""
    m = game.m
    for r in range(len(game.matrix)):
        for c in range(len(game.matrix[r])):
            val = game.matrix[r][c] & 0xF
            tile = game.assets.tiles[val]
            x = game.margin + c * game.tile_size
            y = game.margin + r * game.tile_size
            m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, tile, x, y)


def draw_portal_marker(game: Game, pos: tuple[int, int], pixel_img: Any) -> None:
    """Draw a circular marker around the portal entry/exit using the given pixel image."""
    m = game.m
    row, col = pos

    cx = game.margin + col * game.tile_size + game.tile_size // 2
    cy = game.margin + row * game.tile_size + game.tile_size // 2

    outer_r = PORTAL_OUTER_RADIUS
    inner_r = 7
    outer2 = outer_r * outer_r
    inner2 = inner_r * inner_r

    for dy in range(-outer_r, outer_r + 1):
        for dx in range(-outer_r, outer_r + 1):
            d2 = dx * dx + dy * dy
            if inner2 <= d2 <= outer2:
                m.mlx_put_image_to_window(game.mlx_ptr, game.win_ptr, pixel_img, cx + dx, cy + dy)


def draw_path_upto(game: Game, progress_points: int) -> None:
    """Draw the path segments up to the given progress point index."""
    if progress_points <= 1:
        return
    for i in range(1, progress_points):
        draw_path_segment(game, game.path[i - 1], game.path[i], i)


def redraw_all(game: Game) -> None:
    """Redraw the entire scene: margins, maze tiles, path up to current progress, and portal markers."""
    fill_margins_with_background(game)
    draw_maze_tiles(game)
    draw_path_upto(game, game.path_progress)
    draw_portal_marker(game, game.entry, game.green_px)
    draw_portal_marker(game, game.exit_, game.pink_px)


def key_handler(keycode: int, game: Game) -> int:
    """Handle key presses for quitting, changing color theme, and starting animation."""
    if keycode == 65307:  # ESC
        game.m.mlx_loop_exit(game.mlx_ptr)
        return 0

    if keycode == 99:  # 'c'
        game.color_index = (game.color_index + 1) % len(COLOR_CYCLE)
        game.current_color = COLOR_CYCLE[game.color_index]
        game.assets = game.assets_by_color[game.current_color]
        redraw_all(game)
        return 0

    if keycode == 115:  # 's'
        if not game.animating and game.path_progress >= len(game.path):
            game.path_progress = 0
            redraw_all(game)

        if not game.animating:
            game.animating = True
            game.last_update = time.time()
        return 0

    return 0


def loop_hook(game: Game) -> int:
    """Main loop hook to handle path animation over time."""
    
    if not game.animating:
        return 0

    now = time.time()
    if now - game.last_update < game.animation_speed:
        return 0

    game.last_update = now

    if game.path_progress < len(game.path):
        if game.path_progress == 0:
            game.path_progress = 1
        else:
            i = game.path_progress
            draw_path_segment(game, game.path[i - 1], game.path[i], i)
            game.path_progress += 1
    else:
        game.animating = False

    return 0


def main() -> None:
    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() failed")

    matrix, entry, exit_, moves = load_maze_from_file(MAPA_A_CARGAR)

    max_cols = max(len(r) for r in matrix)
    win_width = MARGIN * 2 + max_cols * TILE_SIZE
    win_height = MARGIN * 2 + len(matrix) * TILE_SIZE

    win_ptr = m.mlx_new_window(mlx_ptr, win_width, win_height, "A-Maze-ing")
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

        path=path,
        path_progress=0,
        animating=False,
        last_update=0.0,
        animation_speed=0.01,
    )

    redraw_all(game)

    m.mlx_key_hook(win_ptr, key_handler, game)
    m.mlx_hook(win_ptr, 17, 0, lambda _p: (m.mlx_loop_exit(mlx_ptr), 0)[1], None)
    m.mlx_loop_hook(mlx_ptr, loop_hook, game)

    m.mlx_loop(mlx_ptr)


if __name__ == "__main__":
    main()