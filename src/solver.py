"""Maze solving utilities (shortest path with BFS)."""

from __future__ import annotations

from collections import deque

NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8

DIRS: dict[int, tuple[int, int, str]] = {
	NORTH: (-1, 0, "N"),
	EAST: (0, 1, "E"),
	SOUTH: (1, 0, "S"),
	WEST: (0, -1, "W"),
}


def _to_row_col(point_xy: tuple[int, int]) -> tuple[int, int]:
	x_coord, y_coord = point_xy
	return y_coord, x_coord


def _in_bounds(row: int, col: int, height: int, width: int) -> bool:
	return 0 <= row < height and 0 <= col < width


def shortest_path_moves(
	maze: list[list[int]],
	entry_xy: tuple[int, int],
	exit_xy: tuple[int, int],
) -> str:
	"""Return shortest valid path as movement string N/E/S/W."""

	if not maze or not maze[0]:
		raise ValueError("maze cannot be empty")

	height = len(maze)
	width = len(maze[0])

	entry = _to_row_col(entry_xy)
	exit_ = _to_row_col(exit_xy)

	if not _in_bounds(entry[0], entry[1], height, width):
		raise ValueError("entry is out of bounds")
	if not _in_bounds(exit_[0], exit_[1], height, width):
		raise ValueError("exit is out of bounds")

	queue: deque[tuple[int, int]] = deque([entry])
	parent: dict[tuple[int, int], tuple[int, int] | None] = {entry: None}
	move_taken: dict[tuple[int, int], str] = {}

	while queue:
		row, col = queue.popleft()
		if (row, col) == exit_:
			break

		walls = maze[row][col]
		for wall_flag, (delta_row, delta_col, step_char) in DIRS.items():
			if walls & wall_flag:
				continue

			n_row = row + delta_row
			n_col = col + delta_col
			if not _in_bounds(n_row, n_col, height, width):
				continue
			if (n_row, n_col) in parent:
				continue

			parent[(n_row, n_col)] = (row, col)
			move_taken[(n_row, n_col)] = step_char
			queue.append((n_row, n_col))

	if exit_ not in parent:
		raise ValueError("No path exists between entry and exit")

	moves: list[str] = []
	cursor = exit_
	while cursor != entry:
		moves.append(move_taken[cursor])
		previous = parent[cursor]
		if previous is None:
			break
		cursor = previous

	moves.reverse()
	return "".join(moves)


