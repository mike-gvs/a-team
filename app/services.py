from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import ApiKey, ConnectorState, DemoRecord, EmailSink, InstallState, PasswordReset, User
from app.providers.base import Completion
from app.providers.registry import build_provider
from app.providers.stub import StubProvider
from app.runtime import RuntimeConfig, secret_value, set_secret
from app.safety import HARD_RULES
from app.security import hash_password, hash_token, new_api_key, new_reset_token, verify_password
from app.settings import Settings
from app.spend import is_capped, record_spend


class ServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def complete_setup(
    db: Session,
    settings: Settings,
    *,
    deployment_name: str,
    require_login: bool,
    admin_username: str | None,
    admin_email: str | None,
    admin_password: str | None,
    model_backend: str,
    brand_name: str,
    accent_color: str,
    monthly_cap_usd: float,
    connectors: dict,
    secrets: dict[str, str],
) -> InstallState:
    install = db.query(InstallState).first()
    if install and install.setup_complete:
        raise ServiceError("Setup is already complete", 403)

    allowed = {"stub", "anthropic"}
    if settings.environment == "test":
        allowed.add("fake-priced")
    if model_backend not in allowed:
        raise ServiceError(f"Unknown model backend: {model_backend}")

    if require_login:
        if not admin_username or not admin_email or not admin_password:
            raise ServiceError("Admin username, email and password are required when login is on")
        if db.query(User).filter_by(username=admin_username).first():
            raise ServiceError("Admin username already exists")
        db.add(
            User(
                username=admin_username,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role="admin",
            )
        )

    for name, value in (secrets or {}).items():
        if value:
            set_secret(db, name, value)

    if model_backend == "anthropic" and not secret_value(db, settings, "ANTHROPIC_API_KEY"):
        raise ServiceError("Missing required secret: ANTHROPIC_API_KEY")

    for name, spec in (connectors or {}).items():
        enabled = bool(spec.get("enabled", False))
        mode = str(spec.get("mode") or "stub")
        row = db.query(ConnectorState).filter_by(name=name).first()
        if row:
            row.enabled = enabled
            row.mode = mode
        else:
            db.add(ConnectorState(name=name, enabled=enabled, mode=mode))
        if mode == "live":
            needed = {
                "email": ["POSTMARK_API_TOKEN"],
                "sms": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"],
            }.get(name, [])
            for var in needed:
                if not secret_value(db, settings, var):
                    raise ServiceError(f"Missing required secret: {var}")

    if not install:
        install = InstallState()
        db.add(install)
        db.flush()
    install.setup_complete = True
    install.deployment_name = deployment_name or "ATeam"
    install.require_login = require_login
    install.model_backend = model_backend
    install.brand_name = brand_name or deployment_name or "ATeam"
    install.accent_color = accent_color or "#EDAA4B"
    install.monthly_cap_usd = float(monthly_cap_usd or 0)
    if not db.query(DemoRecord).filter_by(slug="welcome").first():
        db.add(
            DemoRecord(
                slug="welcome",
                note="Maple Street Books — fictional demo inbox for Scout",
            )
        )
    db.commit()
    db.refresh(install)
    return install


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        raise ServiceError("Invalid username or password", 401)
    return user


def create_user(db: Session, *, username: str, email: str, password: str, role: str) -> User:
    if role not in {"admin", "staff", "viewer"}:
        raise ServiceError("Role must be admin, staff or viewer")
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise ServiceError("Username or email already exists")
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_key(db: Session, *, name: str, created_by: str) -> tuple[str, ApiKey]:
    display, prefix, digest = new_api_key()
    row = ApiKey(name=name, prefix=prefix, key_hash=digest, created_by=created_by)
    db.add(row)
    db.commit()
    db.refresh(row)
    return display, row


def user_for_api_key(db: Session, raw: str) -> User | None:
    digest = hash_token(raw)
    key = db.query(ApiKey).filter_by(key_hash=digest).first()
    if not key:
        return None
    return User(id=0, username=key.created_by, email="", password_hash="", role="admin")


def request_password_reset(db: Session, email: str) -> None:
    user = db.query(User).filter_by(email=email).first()
    if not user:
        return
    raw, digest = new_reset_token()
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
    )
    db.add(
        EmailSink(
            to_addr=email,
            subject="ATeam password reset",
            body=f"Reset token (stub sink): {raw}",
        )
    )
    db.commit()


def apply_password_reset(db: Session, token: str, new_password: str) -> None:
    digest = hash_token(token)
    row = db.query(PasswordReset).filter_by(token_hash=digest).first()
    now = datetime.now(timezone.utc)
    expires = row.expires_at if row else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not row or expires is None or expires < now:
        raise ServiceError("Reset token is invalid or expired", 400)
    user = db.query(User).filter_by(id=row.user_id).first()
    if not user:
        raise ServiceError("User not found", 400)
    user.password_hash = hash_password(new_password)
    db.delete(row)
    db.commit()


def run_agent(
    db: Session,
    settings: Settings,
    runtime: RuntimeConfig,
    *,
    slug: str,
    prompt: str,
) -> Completion:
    backend = runtime.model_backend
    anthropic_key = secret_value(db, settings, "ANTHROPIC_API_KEY")
    provider = build_provider(
        backend,
        skills_dir=settings.skills_dir,
        prompts_dir=settings.prompts_dir,
        anthropic_api_key=anthropic_key,
        slug=slug,
    )
    capped = is_capped(db, runtime.monthly_cap_usd) if provider.paid else False
    if provider.paid and capped:
        fallback = StubProvider(settings.skills_dir, settings.prompts_dir, slug=slug)
        result = fallback.complete(instructions=HARD_RULES, prompt=prompt)
        result.fallback = True
        result.provider = "stub"
        return result
    result = provider.complete(instructions=HARD_RULES, prompt=prompt)
    if result.cost_usd:
        record_spend(db, provider.id, result.cost_usd)
    return result
