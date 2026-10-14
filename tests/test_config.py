from pathlib import Path

import pytest
from app.config_loader import load_connectors_config, load_models_config
from app.db import Base, make_engine, make_session_factory
from app.models import ConnectorState
from app.runtime import StartupError, get_or_create_install, validate_live_connectors
from app.settings import REPO_ROOT, Settings


def test_models_yaml_has_no_connector_secrets():
    text = (REPO_ROOT / "config" / "models" / "default.yaml").read_text()
    assert "TWILIO" not in text
    assert "POSTMARK" not in text


def test_connectors_yaml_has_no_model_keys():
    text = (REPO_ROOT / "config" / "connectors" / "default.yaml").read_text()
    assert "ANTHROPIC" not in text
    assert "MODEL" not in text


def test_yaml_defaults():
    models = load_models_config(REPO_ROOT / "config")
    connectors = load_connectors_config(REPO_ROOT / "config")
    assert models["backend"] == "stub"
    assert connectors["connectors"]["email"]["mode"] == "stub"


def test_live_connector_without_secret_fails_startup(tmp_path: Path):
    engine = make_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 't.db'}",
        ateam_secret_key="test-secret-key-not-for-production",
        postmark_api_token="",
    )
    db = factory()
    get_or_create_install(db, settings)
    row = db.query(ConnectorState).filter_by(name="email").one()
    row.mode = "live"
    row.enabled = True
    db.commit()
    with pytest.raises(StartupError) as exc:
        validate_live_connectors(db, settings)
    assert "POSTMARK_API_TOKEN" in str(exc.value)
    db.close()


def test_production_rejects_placeholder_secret():
    from app.runtime import validate_production_secrets

    settings = Settings(
        environment="production",
        ateam_secret_key="change-me",
        database_url="sqlite:////tmp/unused.db",
    )
    with pytest.raises(StartupError) as exc:
        validate_production_secrets(settings)
    assert "ATEAM_SECRET_KEY" in str(exc.value)
