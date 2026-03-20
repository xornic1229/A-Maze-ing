"""Reusable maze generation module.

This module can be packaged and reused independently.

Basic usage:
    from generator import MazeGenerator

    generator = MazeGenerator(
        width=20,
        height=15,
        entry=(0, 0),
        exit_=(19, 14),
        seed=42,
        perfect=True,
    )
    maze = generator.generate()
    # maze is a list[list[int]] with 4-bit wall masks (N,E,S,W)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random

NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8
FULL_WALLS = NORTH | EAST | SOUTH | WEST

DIRS: dict[int, tuple[int, int]] = {
    NORTH: (-1, 0),
    EAST: (0, 1),
    SOUTH: (1, 0),
    WEST: (0, -1),
}

OPPOSITE: dict[int, int] = {
    NORTH: SOUTH,
    EAST: WEST,
    SOUTH: NORTH,
    WEST: EAST,
}

@dataclass
class MazeGenerator:
    """Generate perfect or imperfect mazes using DFS backtracking."""

    width: int
    height: int
    entry: tuple[int, int]
    exit_: tuple[int, int]
    seed: int | None = None
    perfect: bool = True

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be > 0")
        if self.entry == self.exit_:
            raise ValueError("entry and exit must be different")
        self._check_bounds(self.entry, "entry")
        self._check_bounds(self.exit_, "exit")
        self._rand = random.Random(self.seed)
        self.pattern_placed = False
        self.pattern_omit_reason: str | None = None

    def _check_bounds(self, point: tuple[int, int], key: str) -> None:
        x_coord, y_coord = point
        if x_coord < 0 or x_coord >= self.width or y_coord < 0 or y_coord >= self.height:
            raise ValueError(f"{key} out of bounds")

    def _in_bounds_rc(self, row: int, col: int) -> bool:
        return 0 <= row < self.height and 0 <= col < self.width

    def _entry_row_col(self) -> tuple[int, int]:
        x_coord, y_coord = self.entry
        return y_coord, x_coord

    def _exit_row_col(self) -> tuple[int, int]:
        x_coord, y_coord = self.exit_
        return y_coord, x_coord

    def _new_maze(self) -> list[list[int]]:
        return [[FULL_WALLS for _ in range(self.width)] for _ in range(self.height)]

    def _unvisited_neighbors(
        self,
        row: int,
        col: int,
        visited: set[tuple[int, int]],
    ) -> list[tuple[int, int, int]]:
        neighbors: list[tuple[int, int, int]] = []
        for direction, (delta_row, delta_col) in DIRS.items():
            n_row = row + delta_row
            n_col = col + delta_col
            if self._in_bounds_rc(n_row, n_col) and (n_row, n_col) not in visited:
                neighbors.append((n_row, n_col, direction))
        return neighbors

    def _break_wall(
        self,
        maze: list[list[int]],
        row_a: int,
        col_a: int,
        row_b: int,
        col_b: int,
        direction: int,
    ) -> None:
        maze[row_a][col_a] &= ~direction
        maze[row_b][col_b] &= ~OPPOSITE[direction]

    def _generate_perfect(self) -> list[list[int]]:
        maze = self._new_maze()
        visited: set[tuple[int, int]] = set()
        stack: list[tuple[int, int]] = []

        start = self._entry_row_col()
        stack.append(start)
        visited.add(start)

        while stack:
            row, col = stack[-1]
            neighbors = self._unvisited_neighbors(row, col, visited)

            if not neighbors:
                stack.pop()
                continue

            n_row, n_col, direction = self._rand.choice(neighbors)
            self._break_wall(maze, row, col, n_row, n_col, direction)
            visited.add((n_row, n_col))
            stack.append((n_row, n_col))

        return maze

    def _add_extra_openings(self, maze: list[list[int]], ratio: float = 0.10) -> None:
        candidates: list[tuple[int, int, int]] = []
        for row in range(self.height):
            for col in range(self.width):
                for direction, (delta_row, delta_col) in DIRS.items():
                    n_row = row + delta_row
                    n_col = col + delta_col
                    if not self._in_bounds_rc(n_row, n_col):
                        continue
                    if maze[row][col] & direction:
                        candidates.append((row, col, direction))

        self._rand.shuffle(candidates)
        openings_target = max(1, int(len(candidates) * ratio))
        openings_done = 0
        for row, col, direction in candidates:
            if openings_done >= openings_target:
                break

            delta_row, delta_col = DIRS[direction]
            n_row = row + delta_row
            n_col = col + delta_col
            if not self._in_bounds_rc(n_row, n_col):
                continue
            if not (maze[row][col] & direction):
                continue

            self._break_wall(maze, row, col, n_row, n_col, direction)
            openings_done += 1

    def _force_closed_cell(self, maze: list[list[int]], row: int, col: int) -> None:
        maze[row][col] = FULL_WALLS
        for direction, (delta_row, delta_col) in DIRS.items():
            n_row = row + delta_row
            n_col = col + delta_col
            if not self._in_bounds_rc(n_row, n_col):
                continue
            maze[n_row][n_col] |= OPPOSITE[direction]

    def _pattern_required_positions(
        self,
        start_row: int,
        start_col: int,
        pattern: list[str],
    ) -> set[tuple[int, int]]:
        required: set[tuple[int, int]] = set()
        for row_offset, row_pattern in enumerate(pattern):
            for col_offset, mark in enumerate(row_pattern):
                if mark == "1":
                    required.add((start_row + row_offset, start_col + col_offset))
        return required

    def _is_exact_pattern(
        self,
        maze: list[list[int]],
        required_positions: set[tuple[int, int]],
        start_row: int,
        start_col: int,
        pattern_height: int,
        pattern_width: int,
    ) -> bool:
        # Any F outside required pattern cells is forbidden.
        for row in range(self.height):
            for col in range(self.width):
                if maze[row][col] == FULL_WALLS and (row, col) not in required_positions:
                    return False

        # Inside the 5x7 block, only required positions can be F.
        for row in range(start_row, start_row + pattern_height):
            for col in range(start_col, start_col + pattern_width):
                is_required = (row, col) in required_positions
                is_full = maze[row][col] == FULL_WALLS
                if is_required and not is_full:
                    return False
                if not is_required and is_full:
                    return False

        return True

    def _stamp_42_pattern(
        self,
        maze: list[list[int]],
    ) -> tuple[bool, str | None, set[tuple[int, int]], tuple[int, int, int, int] | None]:
        # 1 means "force this cell fully closed".
        pattern = [
            "1000111",
            "1000001",
            "1110111",
            "0010100",
            "0010111",
        ]

        pattern_height = len(pattern)
        pattern_width = len(pattern[0])

        if self.width < pattern_width + 2 or self.height < pattern_height + 2:
            return False, "maze_too_small", set(), None

        # Place the pattern centered in the maze.
        start_row = (self.height - pattern_height) // 2
        start_col = (self.width - pattern_width) // 2

        required_positions = self._pattern_required_positions(start_row, start_col, pattern)

        entry_row, entry_col = self._entry_row_col()
        exit_row, exit_col = self._exit_row_col()

        for row, col in required_positions:
                if (row, col) in {(entry_row, entry_col), (exit_row, exit_col)}:
                    return False, "interferes_with_portals", set(), None

        for row, col in required_positions:
            self._force_closed_cell(maze, row, col)

        return (
            True,
            None,
            required_positions,
            (start_row, start_col, pattern_height, pattern_width),
        )

    def _has_entry_exit_path(self, maze: list[list[int]]) -> bool:
        start = self._entry_row_col()
        goal = self._exit_row_col()

        queue: deque[tuple[int, int]] = deque([start])
        visited: set[tuple[int, int]] = {start}

        while queue:
            row, col = queue.popleft()
            if (row, col) == goal:
                return True

            walls = maze[row][col]
            for direction, (delta_row, delta_col) in DIRS.items():
                if walls & direction:
                    continue
                n_row = row + delta_row
                n_col = col + delta_col
                if not self._in_bounds_rc(n_row, n_col):
                    continue
                if (n_row, n_col) in visited:
                    continue
                visited.add((n_row, n_col))
                queue.append((n_row, n_col))

        return False

    def generate(self) -> list[list[int]]:
        """Generate the maze and return a matrix of wall bitmasks."""
        max_attempts = 400

        for _ in range(max_attempts):
            maze = self._generate_perfect()

            if not self.perfect:
                self._add_extra_openings(maze)

            pattern_placed, omit_reason, required_positions, bounds = self._stamp_42_pattern(maze)

            if not pattern_placed:
                self.pattern_placed = False
                self.pattern_omit_reason = omit_reason
                return maze

            if bounds is None:
                self.pattern_placed = False
                self.pattern_omit_reason = "pattern_internal_error"
                return maze

            start_row, start_col, pattern_height, pattern_width = bounds

            if not self._is_exact_pattern(
                maze,
                required_positions,
                start_row,
                start_col,
                pattern_height,
                pattern_width,
            ):
                continue

            if self._has_entry_exit_path(maze):
                self.pattern_placed = True
                self.pattern_omit_reason = None
                return maze

        # If after many retries the pattern always blocks the path, keep a valid maze without 42.
        fallback_maze = self._generate_perfect()
        if not self.perfect:
            self._add_extra_openings(fallback_maze)
        self.pattern_placed = False
        self.pattern_omit_reason = "interferes_with_entry_exit_path"
        return fallback_maze


def maze_to_hex_lines(maze: list[list[int]]) -> list[str]:
    """Serialize maze matrix to hexadecimal rows."""

    return ["".join(f"{cell & 0xF:X}" for cell in row) for row in maze]


def validate_walls(maze: list[list[int]]) -> bool:
    """Validate wall consistency between adjacent cells."""

    if not maze or not maze[0]:
        return False

    height = len(maze)
    width = len(maze[0])

    for row in range(height):
        for col in range(width):
            walls = maze[row][col]

            if row > 0 and bool(walls & NORTH) != bool(maze[row - 1][col] & SOUTH):
                return False
            if row < height - 1 and bool(walls & SOUTH) != bool(maze[row + 1][col] & NORTH):
                return False
            if col > 0 and bool(walls & WEST) != bool(maze[row][col - 1] & EAST):
                return False
            if col < width - 1 and bool(walls & EAST) != bool(maze[row][col + 1] & WEST):
                return False

    return True
