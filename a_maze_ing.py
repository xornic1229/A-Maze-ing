"""Launcher kept at repository root for subject-compatible command.

Usage:
    python3 a_maze_ing.py config.txt
"""

from __future__ import annotations
from cli import main

import os
import sys

ROOT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

if __name__ == "__main__":
    raise SystemExit(main())
