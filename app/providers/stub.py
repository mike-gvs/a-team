from __future__ import annotations

from pathlib import Path

from app.providers.base import Completion, ModelProvider


def load_skill_text(skills_dir: str | Path, slug: str) -> str:
    path = Path(skills_dir) / slug / "SKILL.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_prompt_text(prompts_dir: str | Path, slug: str) -> str:
    path = Path(prompts_dir) / f"{slug}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def extract_signature(skill_text: str) -> str:
    lines = skill_text.splitlines()
    capture = False
    collected: list[str] = []
    for line in lines:
        if line.strip() == "## Signature":
            capture = True
            continue
        if capture:
            if line.startswith("## "):
                break
            if line.strip():
                collected.append(line.strip())
    return " ".join(collected)


class StubProvider(ModelProvider):
    id = "stub"
    display_name = "Stub (on this machine, $0)"
    paid = False

    def __init__(self, skills_dir: str, prompts_dir: str, slug: str = "inbox-clerk"):
        self.skills_dir = skills_dir
        self.prompts_dir = prompts_dir
        self.slug = slug

    def complete(self, *, instructions: str, prompt: str) -> Completion:
        skill = load_skill_text(self.skills_dir, self.slug)
        signature = extract_signature(skill) or "Scout here — Maple Street Books inbox."
        prompt_notes = load_prompt_text(self.prompts_dir, self.slug)
        body = (
            f"{signature}\n\n"
            "Draft (stub, no network):\n"
            f"Thanks for writing. I read your note: {prompt.strip()[:280]}\n"
            "I will check with the owner instead of guessing any hours, stock, or prices.\n"
        )
        if "short" in prompt_notes.lower():
            body += "Keeping this short, per the tone notes.\n"
        if instructions:
            body += "\n(Hard rules applied.)"
        return Completion(text=body.strip(), cost_usd=0.0, provider=self.id)

    def reachable(self) -> bool:
        return True
