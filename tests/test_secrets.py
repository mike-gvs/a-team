from pathlib import Path

from app.models import ApiKey, User
from app.runtime import secret_value
from app.services import create_key, user_for_api_key
from app.settings import Settings
from sqlalchemy import inspect
from tests.conftest import complete_wizard
from tests.fixtures.fictional import ANTHROPIC_API_KEY, STAFF_PASSWORD


def test_generates_and_persists_session_key(tmp_path: Path):
    data_dir = str(tmp_path / "data")
    first = Settings(
        environment="development",
        ateam_secret_key="",
        data_dir=data_dir,
    ).resolved_secret_key()
    assert first
    assert "not-for-production" not in first
    key_path = Path(data_dir) / "session.key"
    assert key_path.exists()
    second = Settings(
        environment="development",
        ateam_secret_key="",
        data_dir=data_dir,
    ).resolved_secret_key()
    assert first == second


def test_wizard_secrets_live_in_file_not_database(client, app, settings):
    complete_wizard(
        client,
        model_backend="anthropic",
        secrets={"ANTHROPIC_API_KEY": ANTHROPIC_API_KEY},
    )
    db = app.state.session_factory()
    tables = inspect(db.get_bind()).get_table_names()
    assert "app_secrets" not in tables
    stored = secret_value(db, settings, "ANTHROPIC_API_KEY")
    db.close()
    assert stored == ANTHROPIC_API_KEY
    secrets_file = Path(settings.data_dir) / "secrets.env"
    assert secrets_file.exists()
    assert ANTHROPIC_API_KEY in secrets_file.read_text()


def test_api_key_is_bound_to_user_role(client, app):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password="test-passphrase-ok",
    )
    client.post("/api/login", json={"username": "shop-owner", "password": "test-passphrase-ok"})
    created = client.post(
        "/api/admin/users",
        json={
            "username": "clerk",
            "email": "clerk@example.test",
            "password": STAFF_PASSWORD,
            "role": "staff",
        },
    )
    assert created.status_code == 200
    db = app.state.session_factory()
    staff = db.query(User).filter_by(username="clerk").one()
    display, row = create_key(db, name="staff-bot", user=staff)
    assert row.user_id == staff.id
    assert row.role == "staff"
    owner = user_for_api_key(db, display)
    assert owner is not None
    assert owner.id == staff.id
    assert owner.role == "staff"
    db.close()
    admin_key = client.post("/api/admin/api-keys", json={"name": "admin-bot"})
    assert admin_key.status_code == 200
    body = admin_key.json()
    assert body["role"] == "admin"
    db = app.state.session_factory()
    key_row = db.query(ApiKey).filter_by(prefix=body["prefix"]).one()
    admin = db.query(User).filter_by(username="shop-owner").one()
    assert key_row.user_id == admin.id
    db.close()


def test_unauthenticated_admin_api_redirects_with_location(client):
    response = client.get("/api/admin/logs", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/setup"
