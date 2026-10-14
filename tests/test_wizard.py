from tests.conftest import complete_wizard
from tests.fixtures.fictional import ANTHROPIC_API_KEY

SETUP_FORM = {
    "deployment_name": "Maple Street Books",
    "require_login": "off",
    "admin_username": "",
    "admin_email": "",
    "admin_password": "",
    "model_backend": "stub",
    "brand_name": "Maple Street Books",
    "accent_color": "#EDAA4B",
    "monthly_cap_usd": 0,
    "email_enabled": "off",
    "email_mode": "stub",
    "sms_enabled": "off",
    "sms_mode": "stub",
    "anthropic_api_key": "",
    "postmark_api_token": "",
    "twilio_account_sid": "",
    "twilio_auth_token": "",
    "twilio_from_number": "",
}


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
    assert "/static/js/setup.js" in response.text


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
        secrets={"ANTHROPIC_API_KEY": ANTHROPIC_API_KEY},
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


def test_self_test_allowed_in_setup_mode(client):
    result = client.get("/api/setup/self-test")
    assert result.status_code == 200
    assert result.json()["ok"] is True


def test_self_test_green_on_stub(client):
    complete_wizard(client)
    result = client.get("/api/setup/self-test")
    assert result.status_code == 200
    body = result.json()
    assert body["ok"] is True
    assert body["green"] is True


def test_self_test_requires_auth_after_login_on(client):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password="test-passphrase-ok",
    )
    client.post("/logout")
    denied = client.get("/api/setup/self-test")
    assert denied.status_code == 401
    client.post("/api/login", json={"username": "shop-owner", "password": "test-passphrase-ok"})
    allowed = client.get("/api/setup/self-test")
    assert allowed.status_code == 200
    assert allowed.json()["green"] is True


def test_html_setup_form_ends_on_green_self_test_page(client):
    response = client.post("/setup", data=SETUP_FORM, follow_redirects=False)
    assert response.status_code == 200
    assert "Self-test passed" in response.text
    assert "data-self-test=\"passed\"" in response.text
    assert "gvs-self-test-page ok" in response.text
    assert "health" in response.text
    assert "stub_agent" in response.text
    home = client.get("/")
    assert home.status_code == 200
    assert "Scout" in home.text


def test_html_setup_form_with_login_ends_green(client):
    payload = dict(SETUP_FORM)
    payload.update(
        {
            "require_login": "on",
            "admin_username": "shop-owner",
            "admin_email": "owner@example.test",
            "admin_password": "test-passphrase-ok",
        }
    )
    response = client.post("/setup", data=payload, follow_redirects=False)
    assert response.status_code == 200
    assert "Self-test passed" in response.text
    assert client.get("/api/setup/self-test").status_code == 200
