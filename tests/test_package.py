import re

from app.settings import REPO_ROOT

README = (REPO_ROOT / "README.md").read_text()


def test_license_and_copyright():
    text = (REPO_ROOT / "LICENSE").read_text()
    assert "MIT License" in text
    assert "Copyright (c) 2026 Gold Valley Solutions" in text


def test_readme_skeleton_order():
    headings = re.findall(r"^## .+$", README, flags=re.M)
    expected = [
        "## What it does",
        "## Screenshot",
        "## Prerequisites",
        "## 5-minute setup",
        "## Run it yourself, or have Gold Valley host and manage it",
        "## AI provider and data handling",
        "## What's stubbed",
        "## Configuration",
        "## Architecture",
        "## Profiles and RAM",
        "## Backups",
        "## Support",
        "## License",
    ]
    positions = [README.find(h) for h in expected]
    assert all(p >= 0 for p in positions), headings
    assert positions == sorted(positions)
    prereq = README.find("## Prerequisites")
    quick = README.find("## 5-minute setup")
    assert prereq < quick


def test_readme_lists_credentials_from_env_example():
    env = (REPO_ROOT / ".env.example").read_text()
    creds = []
    for line in env.splitlines():
        if "# credential" in line and "=" in line:
            name = line.split("=", 1)[0].strip()
            creds.append(name)
    assert creds
    for name in creds:
        assert name in README


def test_product_name_is_ateam_one_word():
    assert "ATeam" in README
    assert "AI Team" not in README


def test_gvs_ui_pin():
    html = (REPO_ROOT / "app" / "web" / "templates" / "base.html").read_text()
    assert "gvs-ui@" in html
    static_hit = False
    for path in (REPO_ROOT / "app" / "web" / "templates").rglob("*.html"):
        if "gvs-ui@" in path.read_text():
            static_hit = True
    assert static_hit


def test_no_inline_prompts_in_app():
    hits = []
    for path in (REPO_ROOT / "app").rglob("*.py"):
        text = path.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if "You are" in line or "system prompt" in line:
                hits.append(f"{path}:{i}:{line}")
    assert hits == []


def test_deploy_record_fields():
    path = REPO_ROOT / "deploy" / "DEPLOY_RECORD.md"
    assert path.exists()
    text = path.read_text()
    for field in ("Client:", "URL:", "Host:", "Account owner:", "Support contact:", "Urgency:"):
        assert field in text


def test_release_kit():
    kit = REPO_ROOT / "release-kit"
    assert (kit / "problem.txt").exists()
    assert (kit / "setup.md").exists()
    media = list(kit.glob("*.png")) + list(kit.glob("*.gif")) + list(kit.glob("*.mp4"))
    assert media, "release-kit needs a screenshot"


def test_backup_docs():
    text = (REPO_ROOT / "docs" / "backup.md").read_text()
    assert "nightly" in text.lower()
    assert "restore" in text.lower()
