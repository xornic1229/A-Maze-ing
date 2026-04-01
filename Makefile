PYTHON ?= $(shell if [ -x .venv/bin/python3 ]; then echo .venv/bin/python3; else echo python3; fi)
CONFIG ?= config.txt

.PHONY: install run view debug clean lint lint-strict

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install flake8 mypy

run:
	$(PYTHON) a_maze_ing.py $(CONFIG)

view:
	$(PYTHON) src/mlx_maze_viewer.py map/generated_map.txt

debug:
	$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
	rm -rf build dist

lint:
	flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	$(PYTHON) -m mypy . --strict --ignore-missing-imports
