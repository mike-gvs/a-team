from tests.conftest import complete_wizard


def test_root_redirects_to_setup_when_fresh(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in {302, 303}
    assert "/setup" in response.headers["location"]


def test_setup_page_renders(client):
    response = client.get("/setup")
    assert response.status_code == 200
    assert "Set up ATeam" in response.text
    assert "Stub (default" in response.text
    assert "Anthropic" in response.text
    assert "gvs-ui@0.1.0" in response.text


def test_wizard_defaults_complete_and_block_second_visit(client):
    complete_wizard(client)
    blocked = client.get("/setup", follow_redirects=False)
    assert blocked.status_code in {302, 303, 403}
    home = client.get("/")
    assert home.status_code == 200
    assert "Scout" in home.text
    assert "Login is off" in home.text


def test_wizard_provider_selection_stub_default(client):
    listed = client.get("/api/providers").json()["providers"]
    assert listed[0]["id"] == "stub"
    assert listed[0]["default"] is True
    assert listed[1]["id"] == "anthropic"
    complete_wizard(client)
    runtime = client.get("/api/runtime").json()
    assert runtime["model_backend"] == "stub"


def test_wizard_can_select_anthropic_when_key_present(client):
    complete_wizard(
        client,
        model_backend="anthropic",
        secrets={"ANTHROPIC_API_KEY": "sk-ant-fictional-test-key"},
    )
    runtime = client.get("/api/runtime").json()
    assert runtime["model_backend"] == "anthropic"


def test_wizard_rejects_anthropic_without_key(client):
    response = client.post(
        "/api/setup",
        json={
            "deployment_name": "ATeam",
            "model_backend": "anthropic",
            "require_login": False,
            "connectors": {},
            "secrets": {},
        },
    )
    assert response.status_code == 400
    assert "ANTHROPIC_API_KEY" in response.text


def test_self_test_green_on_stub(client):
    complete_wizard(client)
    result = client.get("/api/setup/self-test")
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is True
    assert body["green"] is True
