*This project has been created as part of the 42 curriculum by jaialons.*

# A-Maze-ing

## Description

A-Maze-ing generates random mazes from a configuration file, exports them in the required hexadecimal format, computes the shortest valid path, and provides visual rendering through MLX.

The project is split into reusable generation/solving modules and a dedicated CLI entrypoint:

- `a_maze_ing.py`: main executable (required command format).
- `src/config.py`: config parsing and validation.
- `src/generator.py`: reusable `MazeGenerator` class and wall consistency checks.
- `src/solver.py`: BFS shortest-path extraction in `N/E/S/W` format.
- `src/mlx_maze_viewer.py`: graphical viewer for generated map files.

## Instructions

### 1) Install

```bash
make install
```

### 2) Generate a maze

```bash
make run
```

Equivalent command:

```bash
python3 a_maze_ing.py config.txt
```

### 3) Open MLX viewer

```bash
make view
```

Or manually with a specific file:

```bash
python3 src/mlx_maze_viewer.py map/generated_map.txt
```

Viewer controls:

- `s`: show/hide animated shortest path.
- `c`: cycle wall color theme.
- `n`: generate a new maze and display it.
- `Esc`: quit.

### 4) Debug and lint

```bash
make debug
make lint
make lint-strict
```

### 5) Clean caches/build artifacts

```bash
make clean
```

## Configuration File Format

One `KEY=VALUE` per line. Empty lines and comments (`# ...`) are ignored.

Mandatory keys:

- `WIDTH`: maze width in cells.
- `HEIGHT`: maze height in cells.
- `ENTRY`: `x,y` coordinates.
- `EXIT`: `x,y` coordinates.
- `OUTPUT_FILE`: output file path.
- `PERFECT`: `True` or `False`.

Optional keys:

- `SEED`: integer seed for reproducibility.
- `ALGORITHM`: currently `dfs`.

Example (`config.txt`):

```ini
WIDTH=30
HEIGHT=18
ENTRY=0,0
EXIT=29,17
OUTPUT_FILE=map/generated_map.txt
PERFECT=True
SEED=42
ALGORITHM=dfs
```

## Output File Format

The output file contains:

1. Maze rows in hexadecimal (one cell per hex digit).
2. One empty line.
3. Entry coordinates as `x,y`.
4. Exit coordinates as `x,y`.
5. Shortest valid path as a movement string using `N/E/S/W`.

All lines end with newline (`\n`).

## Algorithm Choice

### Chosen algorithm

Recursive backtracker implemented iteratively with an explicit stack (DFS).

### Why this algorithm

- Simple and robust for perfect mazes.
- Produces long, interesting corridors.
- Easy to make reproducible using a fixed random seed.
- Easy to adapt for imperfect mazes by adding extra openings.

When `PERFECT=False`, additional random walls are removed after DFS to create loops.

## Reusable Code

Reusable component is centered around `MazeGenerator` in `src/generator.py`.

Basic usage:

```python
from generator import MazeGenerator
from solver import shortest_path_moves

generator = MazeGenerator(
		width=20,
		height=15,
		entry=(0, 0),
		exit_=(19, 14),
		seed=42,
		perfect=True,
)

maze = generator.generate()
moves = shortest_path_moves(maze, (0, 0), (19, 14))
```

Notes:

- Coordinates in generator/solver are `x,y`.
- Export format writes portal coordinates as `x,y`.

The reusable module can be imported directly from `src/`.

## Team and Project Management

### Roles

- `jaialons`: architecture, maze generator, solver, output format, MLX integration, documentation.

### Planning (expected vs real)

- Initial plan: prototype DFS, then parser, then viewer.
- Final execution: viewer came first, then generation pipeline was refactored into reusable modules.
- Improvement made: clear separation between generation, solving, config validation, and visualization.

### What worked well

- Bitmask wall representation kept generation and rendering consistent.
- BFS path extraction made output deterministic and easy to validate.

### What could be improved

- Add automated tests for parser edge cases and wall consistency invariants.
- Add optional multi-algorithm support (Prim/Kruskal).

### Tools used

- Python 3.10+
- MLX Python bindings
- flake8
- mypy
- Make

## Resources

- 42 project subject: A-Maze-ing v2.1.
- Python docs: https://docs.python.org/3/
- Graph traversal references (DFS/BFS):
	- https://en.wikipedia.org/wiki/Depth-first_search
	- https://en.wikipedia.org/wiki/Breadth-first_search

### AI usage

AI was used for:

- Refactoring existing scripts into a cleaner module structure.
- Improving docstrings, typing, and README quality.
- Reviewing Makefile and packaging boilerplate.

All generated content was manually reviewed and adjusted before integration.