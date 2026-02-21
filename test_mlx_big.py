# test_mlx_big.py
# Ejecuta: source .venv/bin/activate && python test_mlx_big.py [archivo_mapa]
# Lee un laberinto desde archivo de texto en formato hexadecimal
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import sys
import os
import glob

import mlx

# ==============================================
# CONFIGURACIÓN: Cambia aquí el mapa a cargar
# ==============================================
MAPA_A_CARGAR = "mapas_prueba/mapa_espiral.txt"  # Cambia a tu mapa deseado o usa argumento de línea de comandos

# Mapas disponibles:
# - "mapa_mini.txt"      (5x5 - pruebas rápidas)
# - "mapa_simple.txt"    (8x7 - básico)  
# - "mapa_prueba.txt"    (20x12 - original)
# - "mapa_complejo.txt"  (16x13 - avanzado)
# - "mapa_espiral.txt"   (11x11 - artístico)
# ==============================================


def load_maze_from_file(filename: str) -> list[list[int]]:
    """
    Load a maze from a text file containing hexadecimal values.
    Each hex value (0-F) represents a wall bitmask:
    0=no walls, 1=N, 2=E, 4=S, 8=W, F=all walls, etc.
    """
    grid = []
    
    try:
        with open(filename, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue
                
                # Parse hexadecimal values from the line
                row = []
                hex_values = line.split()
                for hex_val in hex_values:
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
                    grid.append(row)
                    
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo {filename}")
        # Return a default small maze if file not found
        return [[15, 15, 15], [15, 0, 15], [15, 15, 15]]
    except Exception as e:
        print(f"Error leyendo el archivo {filename}: {e}")
        return [[15, 15, 15], [15, 0, 15], [15, 15, 15]]
    
    if not grid:
        # If no valid data found, return a default maze
        print(f"Warning: No se encontraron datos válidos en {filename}")
        return [[15, 15, 15], [15, 0, 15], [15, 15, 15]]
    
    return grid


@dataclass(frozen=True)
class Assets:
    """Holds MLX image pointers for tiles 0..15."""
    tiles: list[Any]
    tile_w: int
    tile_h: int


def load_tiles(m: mlx.Mlx, mlx_ptr: Any, scale_factor: int = 2) -> Assets:
    """
    Load tiles and return them with scaled dimensions for larger display.
    """
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

    # Tiles originales son 32x32, los escalamos para que se vean más grandes
    base_size = 32
    scaled_size = base_size * scale_factor
    return Assets(tiles=tiles, tile_w=scaled_size, tile_h=scaled_size)


def draw_maze_tiles(
    m: mlx.Mlx,
    mlx_ptr: Any,
    win_ptr: Any,
    grid: list[list[int]],
    assets: Assets,
    margin: int = 20,
    scale_factor: int = 2,
) -> None:
    """
    Draw the maze by placing scaled tile images per cell based on its walls bitmask (0..15).
    Each cell renders its own asset independently based on its wall configuration.
    """
    h = len(grid)
    w = len(grid[0]) if h else 0

    for y in range(h):
        for x in range(w):
            # Each cell draws its own asset based on its hex value (0..15)
            mask = grid[y][x] & 0xF  # ensure 0..15
            img = assets.tiles[mask]
            
            # Position scaled tiles
            px = margin + x * assets.tile_w
            py = margin + y * assets.tile_h
            
            # For larger appearance, we'll draw the image multiple times
            # to create a "scaled" effect
            for dy in range(scale_factor):
                for dx in range(scale_factor):
                    offset_x = px + dx * (assets.tile_w // scale_factor)
                    offset_y = py + dy * (assets.tile_h // scale_factor)
                    m.mlx_put_image_to_window(mlx_ptr, win_ptr, img, offset_x, offset_y)


def print_maze_info(grid: list[list[int]], filename: str) -> None:
    """Print information about the loaded maze."""
    if not grid:
        return
    
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    
    print(f"Laberinto cargado desde: {filename}")
    print(f"Dimensiones: {width} x {height}")
    print(f"Assets utilizados:")
    
    # Count which hex values are used
    used_values = set()
    for row in grid:
        for cell in row:
            used_values.add(cell)
    
    for val in sorted(used_values):
        walls = []
        if val & 1: walls.append("N")
        if val & 2: walls.append("E") 
        if val & 4: walls.append("S")
        if val & 8: walls.append("W")
        wall_str = "+".join(walls) if walls else "sin paredes"
        print(f"  {val:X}: {wall_str}")


def main() -> None:
    print("A-Maze-ing - Visualizador de Laberintos MLX")
    print("===========================================")
    
    # 1) Use configured map file
    maze_file = MAPA_A_CARGAR
    print(f"Cargando mapa: {maze_file}")
    
    # 2) Create MLX wrapper and initialize context
    m = mlx.Mlx()
    mlx_ptr = m.mlx_init()
    if not mlx_ptr:
        raise RuntimeError("mlx_init() returned NULL")

    # 3) Load maze from selected file
    grid = load_maze_from_file(maze_file)
    
    # Print information about the loaded maze
    print_maze_info(grid, maze_file)

    # 4) Load neon XPM tile set (0..F) from ./assets with scaling
    scale_factor = 2  # Make tiles appear 2x larger
    assets = load_tiles(m, mlx_ptr, scale_factor)

    # 5) Compute window size from maze + margins
    margin = 30
    win_w = margin * 2 + len(grid[0]) * assets.tile_w
    win_h = margin * 2 + len(grid) * assets.tile_h

    window_title = f"A-Maze-ing: {os.path.basename(maze_file)} ({len(grid[0])}x{len(grid)})"
    win_ptr = m.mlx_new_window(mlx_ptr, win_w, win_h, window_title)
    if not win_ptr:
        raise RuntimeError("mlx_new_window() returned NULL")

    # 6) Draw maze using scaled tiles
    draw_maze_tiles(m, mlx_ptr, win_ptr, grid, assets, margin=margin, scale_factor=scale_factor)

    # 7) Close handling (ESC + window close button)
    def key_handler(keycode: int, _param: Any) -> int:
        if keycode == 65307:  # ESC
            print(f"Cerrando {maze_file}...")
            m.mlx_loop_exit(mlx_ptr)
            return 0
        return 0

    m.mlx_key_hook(win_ptr, key_handler, None)

    def close_handler(_param: Any) -> int:
        m.mlx_loop_exit(mlx_ptr)
        return 0

    m.mlx_hook(win_ptr, 17, 0, close_handler, None)

    # 8) Loop
    print(f"Ventana creada para '{maze_file}'. Presiona ESC para salir.")
    print("Tip: Para cambiar el mapa, modifica la variable MAPA_A_CARGAR en el código")
    m.mlx_loop(mlx_ptr)

    # 9) Cleanup
    print("¡Hasta la vista!")


if __name__ == "__main__":
    main()
