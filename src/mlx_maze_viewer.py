# mlx_maze_viewer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import os
import time
import mlx

MAPA_A_CARGAR = "mapas_prueba/mapa_masivo.txt"

MARGIN = 2
COLOR_CYCLE = ["green", "pink", "rainbow"]


@dataclass(frozen=True)
class Assets:
    tiles: list[Any]
    tile_width: int
    tile_height: int


# ============================================================
# FILE LOADING
# ============================================================

def load_maze_from_file(filename: str):
    matrix = []
    moves = ""

    with open(filename, "r") as file:
        lines = [line.strip() for line in file]

    # quitar vacíos finales
    while lines and lines[-1] == "":
        lines.pop()

    # última línea = moves, dos anteriores = exit y entry
    moves = lines.pop()
    exit_line = lines.pop()
    entry_line = lines.pop()

    entry = tuple(map(int, entry_line.split(",")))
    exit_ = tuple(map(int, exit_line.split(",")))

    for line in lines:
        if not line:
            continue
        row = []
        for hex_val in line:
            try:
                row.append(int(hex_val, 16) & 0xF)
            except ValueError:
                row.append(0)
        matrix.append(row)

    return matrix, entry, exit_, moves


# ============================================================
# ASSET LOADING
# ============================================================

def load_tiles(m: mlx.Mlx, mlx_ptr: Any, color: str) -> Assets:
    hex_names = "0123456789ABCDEF"
    tiles: list[Any] = []

    for ch in hex_names:
        path = f"assets/{color}/{ch}.xpm"
        result = m.mlx_xpm_file_to_image(mlx_ptr, path)
        if not result or not result[0]:
            raise RuntimeError(f"Asset {ch} could not be loaded from {path}")
        tiles.append(result[0])

    return Assets(tiles=tiles, tile_width=32, tile_height=32)


# ============================================================
# DRAW FUNCTIONS
# ============================================================

def fill_margins_with_background(m, mlx_ptr, window_ptr, window_width, window_height, margin, color):
    margin_path = f"assets/{color}_margin.xpm"
    result = m.mlx_xpm_file_to_image(mlx_ptr, margin_path)
    if not result or not result[0]:
        raise RuntimeError(f"{margin_path} could not be loaded")

    margin_px = result[0]

    # top/bottom
    for y in range(margin):
        for x in range(window_width):
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, x, y)
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, x, window_height - 1 - y)

    # left/right
    for x in range(margin):
        for y in range(window_height):
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, x, y)
            m.mlx_put_image_to_window(mlx_ptr, window_ptr, margin_px, window_width - 1 - x, y)

    return margin_px


def draw_maze_tiles(m, mlx_ptr, window_ptr, matrix, assets, margin):
    for row in range(len(matrix)):
        for col in range(len(matrix[row])):
            cell_value = matrix[row][col] & 0xF
            tile_image = assets.tiles[cell_value]

            draw_x = margin + col * assets.tile_width
            draw_y = margin + row * assets.tile_height

            m.mlx_put_image_to_window(mlx_ptr, window_ptr, tile_image, draw_x, draw_y)


def draw_portal_marker(m, mlx_ptr, win_ptr, position, margin, tile_size, pixel_img):
    row, col = position

    cx = margin + col * tile_size + tile_size // 2
    cy = margin + row * tile_size + tile_size // 2

    outer_r = 10
    inner_r = 7
    outer2 = outer_r * outer_r
    inner2 = inner_r * inner_r

    for dy in range(-outer_r, outer_r + 1):
        for dx in range(-outer_r, outer_r + 1):
            d2 = dx * dx + dy * dy
            if inner2 <= d2 <= outer2:
                m.mlx_put_image_to_window(mlx_ptr, win_ptr, pixel_img, cx + dx, cy + dy)


def change_color(m, mlx_ptr, window_ptr, matrix, assets, margin, w, h, color):
    fill_margins_with_background(m, mlx_ptr, window_ptr, w, h, margin, color)
    draw_maze_tiles(m, mlx_ptr, window_ptr, matrix, assets, margin)


# ============================================================
# PATH LOGIC + LINE DRAWING
# ============================================================

def build_path_from_moves(entry, moves):
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
            # ignorar caracteres basura
            continue
        path.append((row, col))

    return path


def cell_center_px(pos, margin, tile_size):
    r, c = pos
    x = margin + c * tile_size + tile_size // 2
    y = margin + r * tile_size + tile_size // 2
    return x, y


def draw_line_bresenham(m, mlx_ptr, win_ptr, x0, y0, x1, y1, pixel_img, thickness):
    """
    Dibuja una línea fina (Bresenham) con grosor opcional.
    thickness=1 => línea 1px.
    """
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        # grosor: pintamos un pequeño "+" alrededor del punto
        if thickness <= 1:
            m.mlx_put_image_to_window(mlx_ptr, win_ptr, pixel_img, x0, y0)
        else:
            t = thickness // 2
            for oy in range(-t, t + 1):
                for ox in range(-t, t + 1):
                    m.mlx_put_image_to_window(mlx_ptr, win_ptr, pixel_img, x0 + ox, y0 + oy)

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def draw_path_segment(m, mlx_ptr, win_ptr, a_pos, b_pos, margin, tile_size, pixel_img):
    ax, ay = cell_center_px(a_pos, margin, tile_size)
    bx, by = cell_center_px(b_pos, margin, tile_size)

    # línea fina y estética: 1px o 2px si quieres un pelín más visible
    draw_line_bresenham(m, mlx_ptr, win_ptr, ax, ay, bx, by, pixel_img, thickness=4)


# ============================================================
# MAIN
# ============================================================

def main():
    maze_file = MAPA_A_CARGAR

    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() failed")

    matrix, entry, exit_, moves = load_maze_from_file(maze_file)

    tile_size = 32
    margin = MARGIN

    max_cols = max(len(r) for r in matrix)
    win_width = margin * 2 + max_cols * tile_size
    win_height = margin * 2 + len(matrix) * tile_size

    win_ptr = m.mlx_new_window(mlx_ptr, win_width, win_height, "A-Maze-ing")

    assets_by_color = {
        "green": load_tiles(m, mlx_ptr, "green"),
        "pink": load_tiles(m, mlx_ptr, "pink"),
        "rainbow": load_tiles(m, mlx_ptr, "rainbow"),
    }

    # Pixels
    green_px = m.mlx_xpm_file_to_image(mlx_ptr, "assets/green_margin.xpm")[0]
    pink_px = m.mlx_xpm_file_to_image(mlx_ptr, "assets/pink_margin.xpm")[0]
    red_px = m.mlx_xpm_file_to_image(mlx_ptr, "assets/red_pixel.xpm")[0]

    color_index = 0
    current_color = COLOR_CYCLE[color_index]
    assets = assets_by_color[current_color]

    # Path & animation state
    path = build_path_from_moves(entry, moves)
    path_progress = 0          # número de puntos ya "activados"
    animating = False
    last_update = 0.0
    animation_speed = 0.01     # ajusta: 0.005 más rápido / 0.02 más lento

    def draw_path_upto(progress_points: int):
        # Dibuja segmentos entre puntos [0..progress_points-1]
        # Para tener N puntos visibles, hay N-1 segmentos
        if progress_points <= 1:
            return
        for i in range(1, progress_points):
            draw_path_segment(
                m, mlx_ptr, win_ptr,
                path[i - 1], path[i],
                margin, tile_size, red_px
            )

    def redraw_all():
        change_color(m, mlx_ptr, win_ptr, matrix, assets, margin, win_width, win_height, current_color)
        draw_path_upto(path_progress)
        draw_portal_marker(m, mlx_ptr, win_ptr, entry, margin, tile_size, green_px)
        draw_portal_marker(m, mlx_ptr, win_ptr, exit_, margin, tile_size, pink_px)

    redraw_all()

    def key_handler(keycode, _param):
        nonlocal color_index, current_color, assets
        nonlocal animating, last_update, path_progress

        # ESC
        if keycode == 65307:
            m.mlx_loop_exit(mlx_ptr)
            return 0

        # 'c' cambiar tema
        if keycode == 99:
            color_index = (color_index + 1) % len(COLOR_CYCLE)
            current_color = COLOR_CYCLE[color_index]
            assets = assets_by_color[current_color]
            redraw_all()
            return 0

        # 's' animar entrada -> salida
        if keycode == 115:
            # si ya terminó, reinicia y vuelve a animar
            if not animating and path_progress >= len(path):
                path_progress = 0
                redraw_all()

            if not animating:
                animating = True
                last_update = time.time()
            return 0

        return 0

    m.mlx_key_hook(win_ptr, key_handler, None)

    def loop_hook(_param):
        nonlocal path_progress, animating, last_update

        if not animating:
            return 0

        now = time.time()
        if now - last_update < animation_speed:
            return 0

        last_update = now

        # avanzamos 1 punto (y dibujamos el segmento nuevo)
        if path_progress < len(path):
            # cuando pasamos de k puntos a k+1, el segmento nuevo es (k-1 -> k)
            # pero cuidado en k=0
            if path_progress == 0:
                path_progress = 1
            else:
                i = path_progress
                draw_path_segment(
                    m, mlx_ptr, win_ptr,
                    path[i - 1], path[i],
                    margin, tile_size, red_px
                )
                path_progress += 1
        else:
            animating = False

        return 0

    m.mlx_loop_hook(mlx_ptr, loop_hook, None)
    m.mlx_loop(mlx_ptr)


if __name__ == "__main__":
    main()