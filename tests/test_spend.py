from tests.conftest import complete_wizard


def test_fake_priced_cap_trips_and_falls_back(client):
    complete_wizard(client, model_backend="fake-priced", monthly_cap_usd=0.01)
    first = client.post("/api/agents/inbox-clerk/messages", json={"prompt": "one"})
    assert first.status_code == 200
    assert first.json()["fallback"] is False
    health = client.get("/health").json()
    assert health["spend"]["capped"] is True
    second = client.post("/api/agents/inbox-clerk/messages", json={"prompt": "two"})
    assert second.status_code == 200
    assert second.json()["fallback"] is True
    assert second.json()["provider"] == "stub"
