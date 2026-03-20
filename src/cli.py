"""Main entrypoint logic for A-Maze-ing.

Usage:
    python3 a_maze_ing.py config.txt
"""

from __future__ import annotations

import os

from config import MazeConfig, read_config
from generator import MazeGenerator, maze_to_hex_lines, validate_walls
from solver import shortest_path_moves


def write_output_file(
    output_path: str,
    maze: list[list[int]],
    entry_xy: tuple[int, int],
    exit_xy: tuple[int, int],
    moves: str,
) -> None:
    """Write maze matrix plus metadata in the expected format."""

    lines = maze_to_hex_lines(maze)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as output_file:
        for line in lines:
            output_file.write(f"{line}\n")

        output_file.write("\n")
        output_file.write(f"{entry_xy[0]},{entry_xy[1]}\n")
        output_file.write(f"{exit_xy[0]},{exit_xy[1]}\n")
        output_file.write(f"{moves}\n")


def run(config: MazeConfig) -> None:
    """Generate maze, solve path, and persist output file."""

    generator = MazeGenerator(
        width=config.width,
        height=config.height,
        entry=config.entry,
        exit_=config.exit_,
        seed=config.seed,
        perfect=config.perfect,
    )
    maze = generator.generate()

    if not validate_walls(maze):
        raise ValueError("Generated maze is inconsistent (wall mismatch)")

    moves = shortest_path_moves(maze, config.entry, config.exit_)
    write_output_file(config.output_file, maze, config.entry, config.exit_, moves)

    print(f"Maze generated in {config.output_file}")
    if not generator.pattern_placed:
        reason = generator.pattern_omit_reason or "unknown_reason"
        print(
            "Warning: '42' pattern omitted "
            f"({reason}). Allowed causes: maze too small or interference with portals/path."
        )


def main(argv: list[str] | None = None) -> int:
    import sys

    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python3 a_maze_ing.py config.txt")
        return 2

    config_path = args[0]

    try:
        config = read_config(config_path)
        run(config)
    except FileNotFoundError:
        print(f"Error: config file not found: {config_path}")
        return 1
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    except OSError as exc:
        print(f"I/O Error: {exc}")
        return 1

    return 0
