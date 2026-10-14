from tests.conftest import complete_wizard
from tests.fixtures.fictional import ADMIN_PASSWORD, STAFF_PASSWORD


def test_admin_redirects_to_login_when_login_on(client):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password=ADMIN_PASSWORD,
    )
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in {302, 303}
    assert "/login" in response.headers["location"]


def test_admin_loads_with_banner_when_login_off(client):
    complete_wizard(client, require_login=False)
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Login is off" in response.text


def test_admin_login_success(client):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password=ADMIN_PASSWORD,
    )
    login = client.post(
        "/api/login",
        json={"username": "shop-owner", "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    admin = client.get("/admin")
    assert admin.status_code == 200


def test_staff_cannot_open_settings(client):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password=ADMIN_PASSWORD,
    )
    client.post("/api/login", json={"username": "shop-owner", "password": ADMIN_PASSWORD})
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
    client.post("/logout")
    client.post("/api/login", json={"username": "clerk", "password": STAFF_PASSWORD})
    settings_page = client.get("/admin/settings")
    assert settings_page.status_code == 403


def test_password_reset_uses_email_sink(client):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password=ADMIN_PASSWORD,
    )
    client.post("/api/login", json={"username": "shop-owner", "password": ADMIN_PASSWORD})
    reset = client.post("/api/password-reset", json={"email": "owner@example.test"})
    assert reset.status_code == 200
    sink = client.get("/api/email-sink").json()
    assert sink["messages"]
    body = sink["messages"][0]["body"]
    token = body.rsplit(" ", 1)[-1]
    apply = client.post(
        "/api/password-reset/apply",
        json={"token": token, "new_password": "new-passphrase-ok"},
    )
    assert apply.status_code == 200
    client.post("/logout")
    again = client.post(
        "/api/login",
        json={"username": "shop-owner", "password": "new-passphrase-ok"},
    )
    assert again.status_code == 200
