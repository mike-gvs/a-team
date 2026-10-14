from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import ConnectorState
from app.providers.registry import build_provider
from app.runtime import RuntimeConfig, secret_value
from app.settings import Settings
from app.spend import is_capped, month_spend


def _db_ok(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — health must report, not raise
        return False


def build_health(db: Session, settings: Settings, runtime: RuntimeConfig) -> dict:
    db_ok = _db_ok(db)
    provider = build_provider(
        runtime.model_backend,
        skills_dir=settings.skills_dir,
        prompts_dir=settings.prompts_dir,
        anthropic_api_key=secret_value(db, settings, "ANTHROPIC_API_KEY"),
    )
    model_ok = bool(db_ok and provider.reachable())
    connectors: dict[str, str] = {}
    connector_error = False
    for row in db.query(ConnectorState).all() if db_ok else []:
        connectors[row.name] = "live" if row.mode == "live" and row.enabled else "stub"
        if row.mode == "live" and row.enabled:
            needed = {
                "email": "POSTMARK_API_TOKEN",
                "sms": "TWILIO_AUTH_TOKEN",
            }.get(row.name)
            if needed and not secret_value(db, settings, needed):
                connectors[row.name] = "error"
                connector_error = True
    paid = runtime.model_backend != "stub"
    spend_capped = bool(paid and db_ok and is_capped(db, runtime.monthly_cap_usd))
    ok = db_ok and model_ok and not connector_error
    return {
        "app": "ok" if ok else "error",
        "db": "ok" if db_ok else "error",
        "model": {
            "backend": runtime.model_backend,
            "reachable": model_ok,
        },
        "connectors": connectors,
        "version": settings.version,
        "image_tag": settings.image_tag,
        "spend": {
            "month_usd": month_spend(db) if db_ok else 0.0,
            "cap_usd": runtime.monthly_cap_usd,
            "capped": spend_capped,
        },
    }
