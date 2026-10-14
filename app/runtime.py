from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.config_loader import connector_entries, load_connectors_config, load_models_config
from app.models import AppSecret, ConnectorState, InstallState
from app.settings import PLACEHOLDER_VALUES, Settings


class StartupError(RuntimeError):
    pass


@dataclass
class RuntimeConfig:
    setup_complete: bool
    deployment_name: str
    require_login: bool
    model_backend: str
    brand_name: str
    accent_color: str
    logo_path: str
    monthly_cap_usd: float
    connectors: dict[str, dict]


def get_or_create_install(db: Session, settings: Settings) -> InstallState:
    row = db.query(InstallState).first()
    if row:
        return row
    models_cfg = load_models_config(settings.config_dir)
    row = InstallState(
        setup_complete=False,
        deployment_name="ATeam",
        require_login=False,
        model_backend=str(models_cfg.get("backend") or "stub"),
        monthly_cap_usd=float(models_cfg.get("monthly_cap_usd") or 0),
    )
    db.add(row)
    connectors_cfg = load_connectors_config(settings.config_dir)
    for name, spec in connector_entries(connectors_cfg).items():
        db.add(
            ConnectorState(
                name=name,
                enabled=bool(spec.get("enabled", False)),
                mode=str(spec.get("mode") or "stub"),
            )
        )
    db.commit()
    db.refresh(row)
    return row


def secret_value(db: Session, settings: Settings, name: str) -> str:
    env_map = {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "POSTMARK_API_TOKEN": settings.postmark_api_token,
        "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
        "TWILIO_FROM_NUMBER": settings.twilio_from_number,
        "POSTGRES_PASSWORD": settings.postgres_password,
        "ATEAM_SECRET_KEY": settings.ateam_secret_key,
    }
    env_val = (env_map.get(name) or "").strip()
    if env_val:
        return env_val
    row = db.query(AppSecret).filter_by(name=name).first()
    return (row.value if row else "").strip()


def set_secret(db: Session, name: str, value: str) -> None:
    if not value:
        return
    row = db.query(AppSecret).filter_by(name=name).first()
    if row:
        row.value = value
    else:
        db.add(AppSecret(name=name, value=value))
    db.commit()


def load_runtime(db: Session, settings: Settings) -> RuntimeConfig:
    install = get_or_create_install(db, settings)
    connectors = {
        row.name: {"enabled": row.enabled, "mode": row.mode}
        for row in db.query(ConnectorState).all()
    }
    return RuntimeConfig(
        setup_complete=install.setup_complete,
        deployment_name=install.deployment_name,
        require_login=install.require_login,
        model_backend=install.model_backend,
        brand_name=install.brand_name,
        accent_color=install.accent_color,
        logo_path=install.logo_path,
        monthly_cap_usd=install.monthly_cap_usd,
        connectors=connectors,
    )


def validate_production_secrets(settings: Settings) -> None:
    if not settings.is_production:
        return
    secret = settings.resolved_secret_key()
    if not secret or secret in PLACEHOLDER_VALUES or "not-for-production" in secret:
        raise StartupError("ATEAM_SECRET_KEY is missing or a placeholder (ENVIRONMENT=production)")
    password = settings.postgres_password
    if settings.database_url.startswith("sqlite"):
        return
    if not password or password in PLACEHOLDER_VALUES:
        raise StartupError("POSTGRES_PASSWORD is missing or a placeholder (ENVIRONMENT=production)")


def validate_live_connectors(db: Session, settings: Settings) -> None:
    connectors_cfg = load_connectors_config(settings.config_dir)
    specs = connector_entries(connectors_cfg)
    for row in db.query(ConnectorState).all():
        if row.mode != "live":
            continue
        spec = specs.get(row.name, {})
        for var in spec.get("secrets") or []:
            if not secret_value(db, settings, str(var)):
                raise StartupError(f"Missing required secret: {var}")


def validate_model_backend(db: Session, settings: Settings, backend: str) -> None:
    if backend == "anthropic":
        if not secret_value(db, settings, "ANTHROPIC_API_KEY"):
            raise StartupError("Missing required secret: ANTHROPIC_API_KEY")
    if backend == "stub":
        return


def run_startup_checks(factory: sessionmaker, settings: Settings) -> None:
    validate_production_secrets(settings)
    db = factory()
    try:
        get_or_create_install(db, settings)
        runtime = load_runtime(db, settings)
        if runtime.setup_complete:
            validate_model_backend(db, settings, runtime.model_backend)
        validate_live_connectors(db, settings)
    finally:
        db.close()
