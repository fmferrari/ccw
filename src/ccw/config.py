from __future__ import annotations

from pathlib import Path


DEFAULT_CONFIG = {
    "config_version": 1,
}


def default_config_text() -> str:
    return "".join(f"{key}: {value}\n" for key, value in DEFAULT_CONFIG.items())


def load_config(path: Path) -> dict[str, int | bool | str]:
    config: dict[str, int | bool | str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid config line: {raw_line!r}")
        key, raw_value = line.split(":", 1)
        config[key.strip()] = _parse_scalar(raw_value.strip())
    return config


def _parse_scalar(value: str) -> int | bool | str:
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value
