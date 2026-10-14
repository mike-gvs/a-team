from app.models import EmailSink, SpendEvent
from tests.conftest import complete_wizard
from tests.fixtures.fictional import ADMIN_PASSWORD


def test_purge_logs_truncates_spend_and_email_sink(client):
    complete_wizard(
        client,
        require_login=True,
        admin_username="shop-owner",
        admin_email="owner@example.test",
        admin_password=ADMIN_PASSWORD,
        model_backend="fake-priced",
        monthly_cap_usd=0.01,
    )
    client.post("/api/login", json={"username": "shop-owner", "password": ADMIN_PASSWORD})
    first = client.post("/api/agents/inbox-clerk/messages", json={"prompt": "one"})
    assert first.status_code == 200
    reset = client.post("/api/password-reset", json={"email": "owner@example.test"})
    assert reset.status_code == 200
    logs = client.get("/api/admin/logs")
    assert logs.status_code == 200
    body = logs.json()
    assert body["spend_events"]
    assert body["email_sink"]
    purged = client.post("/api/admin/purge-logs")
    assert purged.status_code == 200
    assert purged.json()["ok"] is True
    empty = client.get("/api/admin/logs").json()
    assert empty["spend_events"] == []
    assert empty["email_sink"] == []
    health = client.get("/health").json()
    assert health["spend"]["month_usd"] == 0


def test_purge_logs_service_counts(app):
    factory = app.state.session_factory
    db = factory()
    db.add(SpendEvent(provider="fake-priced", amount_usd=0.01))
    db.add(EmailSink(to_addr="owner@example.test", subject="n", body="b"))
    db.commit()
    from app.services import purge_logs

    result = purge_logs(db)
    assert result["spend_events"] == 1
    assert result["email_sink"] == 1
    db.close()
