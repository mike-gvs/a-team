#!/usr/bin/env python3
"""Validate skills/*/SKILL.md frontmatter against the Agent Skills spec subset."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill = skill_dir / "SKILL.md"
    if not skill.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]
    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return [f"{skill_dir.name}: missing YAML frontmatter"]
    parts = text.split("---", 2)
    if len(parts) < 3:
        return [f"{skill_dir.name}: incomplete frontmatter"]
    data = yaml.safe_load(parts[1]) or {}
    name = str(data.get("name") or "")
    description = str(data.get("description") or "")
    if not NAME_RE.match(name) or len(name) > 64:
        errors.append(f"{skill_dir.name}: invalid name {name!r}")
    if name != skill_dir.name:
        errors.append(f"{skill_dir.name}: name does not match directory")
    if not description or len(description) > 1024:
        errors.append(f"{skill_dir.name}: invalid description")
    return errors


def main() -> int:
    skills = sorted((ROOT / "skills").glob("*/"))
    if not skills:
        print("no skills found", file=sys.stderr)
        return 1
    errors: list[str] = []
    for folder in skills:
        errors.extend(validate(folder))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ok ({len(skills)} skill(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
