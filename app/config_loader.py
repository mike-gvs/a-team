from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    pass


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config must be a mapping: {path}")
    return data


def load_models_config(config_dir: str | Path) -> dict[str, Any]:
    path = Path(config_dir) / "models" / "default.yaml"
    return _read_yaml(path)


def load_connectors_config(config_dir: str | Path) -> dict[str, Any]:
    path = Path(config_dir) / "connectors" / "default.yaml"
    return _read_yaml(path)


def default_backend(models_cfg: dict[str, Any]) -> str:
    return str(models_cfg.get("backend") or "stub")


def default_cap(models_cfg: dict[str, Any]) -> float:
    return float(models_cfg.get("monthly_cap_usd") or 0)


def connector_entries(connectors_cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = connectors_cfg.get("connectors") or {}
    return {str(k): dict(v or {}) for k, v in raw.items()}
