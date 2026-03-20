"""Configuration parser for A-Maze-ing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MazeConfig:
    """Validated runtime configuration for maze generation."""

    width: int
    height: int
    entry: tuple[int, int]
    exit_: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None
    algorithm: str = "dfs"


def _parse_coord(raw_value: str, key: str) -> tuple[int, int]:
    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) != 2:
        raise ValueError(f"{key} must have format x,y")

    try:
        x = int(parts[0])
        y = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"{key} must contain integer values") from exc

    return x, y


def _parse_bool(raw_value: str, key: str) -> bool:
    value = raw_value.strip().lower()
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"{key} must be True or False")


def _validate_bounds(config: MazeConfig) -> None:
    if config.width <= 0 or config.height <= 0:
        raise ValueError("WIDTH and HEIGHT must be > 0")

    if config.entry == config.exit_:
        raise ValueError("ENTRY and EXIT must be different")

    for key, (x_coord, y_coord) in (("ENTRY", config.entry), ("EXIT", config.exit_)):
        if x_coord < 0 or x_coord >= config.width or y_coord < 0 or y_coord >= config.height:
            raise ValueError(f"{key} is out of maze bounds")


def read_config(path: str) -> MazeConfig:
    """Read and validate a KEY=VALUE maze configuration file."""

    raw_values: dict[str, str] = {}

    with open(path, "r", encoding="utf-8") as config_file:
        for line_number, raw_line in enumerate(config_file, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                raise ValueError(f"Invalid config line {line_number}: '{line}'")

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or not value:
                raise ValueError(f"Invalid config line {line_number}: '{line}'")

            raw_values[key.upper()] = value

    required = ["WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"]
    for key in required:
        if key not in raw_values:
            raise ValueError(f"Missing mandatory config key: {key}")

    try:
        width = int(raw_values["WIDTH"])
        height = int(raw_values["HEIGHT"])
    except ValueError as exc:
        raise ValueError("WIDTH and HEIGHT must be valid integers") from exc

    entry = _parse_coord(raw_values["ENTRY"], "ENTRY")
    exit_ = _parse_coord(raw_values["EXIT"], "EXIT")
    perfect = _parse_bool(raw_values["PERFECT"], "PERFECT")

    seed: int | None = None
    if "SEED" in raw_values:
        try:
            seed = int(raw_values["SEED"])
        except ValueError as exc:
            raise ValueError("SEED must be an integer") from exc

    algorithm = raw_values.get("ALGORITHM", "dfs").strip().lower()

    config = MazeConfig(
        width=width,
        height=height,
        entry=entry,
        exit_=exit_,
        output_file=raw_values["OUTPUT_FILE"],
        perfect=perfect,
        seed=seed,
        algorithm=algorithm,
    )
    _validate_bounds(config)
    return config
