from tests.conftest import complete_wizard


def test_health_shape_before_and_after_setup(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    for key in ("app", "model", "connectors", "version", "image_tag"):
        assert key in body
    assert body["app"] == "ok"
    assert body["model"]["backend"] == "stub"
    complete_wizard(client)
    again = client.get("/health").json()
    assert again["model"]["backend"] == "stub"
    assert again["connectors"]["email"] == "stub"
    assert again["connectors"]["sms"] == "stub"
    assert again["version"] == "0.1.0"
    assert again["image_tag"] == "0.1.0-test"
