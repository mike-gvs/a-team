from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ConnectorState
from app.providers.registry import build_provider
from app.runtime import RuntimeConfig, secret_value
from app.settings import Settings
from app.spend import is_capped, month_spend


def build_health(db: Session, settings: Settings, runtime: RuntimeConfig) -> dict:
    provider = build_provider(
        runtime.model_backend,
        skills_dir=settings.skills_dir,
        prompts_dir=settings.prompts_dir,
        anthropic_api_key=secret_value(db, settings, "ANTHROPIC_API_KEY"),
    )
    model_ok = provider.reachable()
    connectors: dict[str, str] = {}
    for row in db.query(ConnectorState).all():
        connectors[row.name] = "live" if row.mode == "live" and row.enabled else "stub"
        if row.mode == "live" and row.enabled:
            # live is reported as live only when the secret is present; else error
            needed = {
                "email": "POSTMARK_API_TOKEN",
                "sms": "TWILIO_AUTH_TOKEN",
            }.get(row.name)
            if needed and not secret_value(db, settings, needed):
                connectors[row.name] = "error"
    paid = runtime.model_backend != "stub"
    spend_capped = bool(paid and is_capped(db, runtime.monthly_cap_usd))
    return {
        "app": "ok",
        "model": {
            "backend": runtime.model_backend,
            "reachable": model_ok,
        },
        "connectors": connectors,
        "version": settings.version,
        "image_tag": settings.image_tag,
        "spend": {
            "month_usd": month_spend(db),
            "cap_usd": runtime.monthly_cap_usd,
            "capped": spend_capped,
        },
    }
