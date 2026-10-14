from app.models import ConnectorState, InstallState
from tests.conftest import complete_wizard


def test_health_shape_before_and_after_setup(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    for key in ("app", "model", "connectors", "version", "image_tag", "db"):
        assert key in body
    assert body["app"] == "ok"
    assert body["db"] == "ok"
    assert body["model"]["backend"] == "stub"
    complete_wizard(client)
    again = client.get("/health").json()
    assert again["model"]["backend"] == "stub"
    assert again["connectors"]["email"] == "stub"
    assert again["connectors"]["sms"] == "stub"
    assert again["version"] == "0.1.0"
    assert again["image_tag"] == "0.1.0-test"


def test_health_503_when_model_unreachable(client, app):
    complete_wizard(client)
    db = app.state.session_factory()
    install = db.query(InstallState).one()
    install.model_backend = "anthropic"
    db.commit()
    db.close()
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["app"] == "error"
    assert body["model"]["reachable"] is False


def test_health_503_when_live_connector_missing_secret(client, app):
    complete_wizard(client)
    db = app.state.session_factory()
    row = db.query(ConnectorState).filter_by(name="email").one()
    row.mode = "live"
    row.enabled = True
    db.commit()
    db.close()
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["app"] == "error"
    assert body["connectors"]["email"] == "error"
