from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("ATEAM_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("VERSION", "0.1.0")
os.environ.setdefault("IMAGE_TAG", "0.1.0-test")
os.environ.pop("ANTHROPIC_API_KEY", None)

from app.main import create_app  # noqa: E402
from app.settings import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    db_path = tmp_path / "ateam.db"
    return Settings(
        environment="test",
        database_url=f"sqlite:///{db_path}",
        ateam_secret_key="test-secret-key-not-for-production",
        version="0.1.0",
        image_tag="0.1.0-test",
        anthropic_api_key="",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def complete_wizard(client: TestClient, **overrides) -> dict:
    payload = {
        "deployment_name": "Maple Street Books",
        "require_login": False,
        "model_backend": "stub",
        "brand_name": "Maple Street Books",
        "accent_color": "#EDAA4B",
        "monthly_cap_usd": 0,
        "connectors": {
            "email": {"enabled": False, "mode": "stub"},
            "sms": {"enabled": False, "mode": "stub"},
        },
        "secrets": {},
    }
    payload.update(overrides)
    response = client.post("/api/setup", json=payload)
    assert response.status_code == 200, response.text
    return response.json()
