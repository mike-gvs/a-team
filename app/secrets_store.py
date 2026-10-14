from __future__ import annotations

import secrets
from pathlib import Path

SESSION_KEY_NAME = "session.key"
SECRETS_FILE_NAME = "secrets.env"


def data_path(data_dir: str, name: str) -> Path:
    return Path(data_dir) / name


def read_secrets_file(data_dir: str) -> dict[str, str]:
    path = data_path(data_dir, SECRETS_FILE_NAME)
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        out[name.strip()] = value.strip()
    return out


def write_secret(data_dir: str, name: str, value: str) -> None:
    if not value:
        return
    path = data_path(data_dir, SECRETS_FILE_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = read_secrets_file(data_dir)
    current[name] = value
    lines = ["# ATeam wizard secrets. Not included in make backup."]
    for key, item in current.items():
        lines.append(f"{key}={item}")
    path.write_text("\n".join(lines) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def persist_or_read_session_key(data_dir: str) -> str:
    path = data_path(data_dir, SESSION_KEY_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text().strip()
        if existing:
            return existing
    key = secrets.token_urlsafe(48)
    path.write_text(key + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key
