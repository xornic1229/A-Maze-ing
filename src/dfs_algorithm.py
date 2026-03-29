"""Backward-compatible helpers for DFS generation.

Use MazeGenerator from generator.py for new code.
"""

from __future__ import annotations

from generator import MazeGenerator


def generate_perfect_maze(
    rows: int,
    cols: int,
    entry: tuple[int, int],
    seed: int | None = None,
) -> list[list[int]]:
    """Legacy wrapper to generate a perfect maze."""

    row, col = entry
    generator = MazeGenerator(
        width=cols,
        height=rows,
        entry=(col, row),
        exit_=(cols - 1, rows - 1),
        seed=seed,
        perfect=True,
    )
    return generator.generate()
