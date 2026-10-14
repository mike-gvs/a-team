from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.config_loader import connector_entries, load_connectors_config, load_models_config
from app.db import Base, make_engine, make_session_factory
from app.health import build_health
from app.models import ApiKey, EmailSink, User
from app.providers.registry import available_providers
from app.runtime import (
    StartupError,
    load_runtime,
    run_startup_checks,
    secret_value,
)
from app.services import (
    ServiceError,
    apply_password_reset,
    authenticate,
    complete_setup,
    create_key,
    create_user,
    list_log_rows,
    purge_logs,
    request_password_reset,
    run_agent,
    user_for_api_key,
)
from app.settings import REPO_ROOT, Settings, load_settings
from app.spend import is_capped, month_spend

TEMPLATE_DIR = Path(__file__).resolve().parent / "web" / "templates"
GVS_UI_VERSION = "0.1.0"


class SetupIn(BaseModel):
    deployment_name: str = "ATeam"
    require_login: bool = False
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    model_backend: str = "stub"
    brand_name: str = "ATeam"
    accent_color: str = "#EDAA4B"
    monthly_cap_usd: float = 0
    connectors: dict[str, dict[str, Any]] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)


class MessageIn(BaseModel):
    prompt: str


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(BaseModel):
    username: str
    email: str
    password: str
    role: str = "staff"


class KeyIn(BaseModel):
    name: str = "machine"


class ResetIn(BaseModel):
    email: str


class ResetApplyIn(BaseModel):
    token: str
    new_password: str


def _templates() -> Jinja2Templates:
    return Jinja2Templates(directory=str(TEMPLATE_DIR))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    engine = make_engine(settings.resolved_database_url())
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    try:
        run_startup_checks(factory, settings)
    except StartupError:
        if settings.environment != "test":
            raise

    app = FastAPI(title="ATeam", version=settings.version)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.resolved_secret_key() or "test-only-session-key",
        session_cookie="ateam_session",
        max_age=settings.session_hours * 3600,
        https_only=False,
        same_site="lax",
    )
    templates = _templates()
    static_dir = REPO_ROOT / "static"
    gvs_dir = REPO_ROOT / "packages" / "gvs-ui"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    if gvs_dir.exists():
        app.mount("/gvs-ui", StaticFiles(directory=str(gvs_dir)), name="gvs-ui")

    def db_session() -> Session:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def ctx(request: Request, db: Session, extra: dict | None = None) -> dict:
        runtime = load_runtime(db, settings)
        data = {
            "request": request,
            "gvs_ui": GVS_UI_VERSION,
            "product": "ATeam",
            "runtime": runtime,
            "login_off": runtime.setup_complete and not runtime.require_login,
            "user": request.session.get("user"),
        }
        if extra:
            data.update(extra)
        return data

    def current_user(request: Request, db: Session) -> dict | None:
        runtime = load_runtime(db, settings)
        if runtime.setup_complete and not runtime.require_login:
            return {"id": 0, "username": "demo", "role": "admin"}
        sess = request.session.get("user")
        if sess:
            return sess
        auth = request.headers.get("authorization") or request.headers.get("x-api-key")
        raw = ""
        if auth and auth.lower().startswith("bearer "):
            raw = auth.split(" ", 1)[1].strip()
        elif auth:
            raw = auth.strip()
        if raw:
            user = user_for_api_key(db, raw)
            if user:
                return {"id": user.id, "username": user.username, "role": user.role}
        return None

    def require_user(request: Request, db: Session, *, role: str | None = None) -> dict:
        runtime = load_runtime(db, settings)
        if not runtime.setup_complete:
            raise HTTPException(status_code=302, detail="setup")
        user = current_user(request, db)
        if runtime.require_login and not user:
            raise HTTPException(status_code=401, detail="login required")
        if not user:
            user = {"id": 0, "username": "demo", "role": "admin"}
        if role == "admin" and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="admin only")
        return user

    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Request, exc: ServiceError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @app.get("/health")
    def health(db: Session = Depends(db_session)):
        runtime = load_runtime(db, settings)
        payload = build_health(db, settings, runtime)
        status = 200 if payload.get("app") == "ok" else 503
        return JSONResponse(payload, status_code=status)

    @app.get("/api/health")
    def api_health(db: Session = Depends(db_session)):
        return health(db)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, db: Session = Depends(db_session)):
        runtime = load_runtime(db, settings)
        if not runtime.setup_complete:
            return RedirectResponse("/setup", status_code=302)
        user = current_user(request, db)
        if runtime.require_login and not user:
            return RedirectResponse("/login", status_code=302)
        return templates.TemplateResponse("home.html", ctx(request, db))

    @app.get("/setup", response_class=HTMLResponse)
    def setup_page(request: Request, db: Session = Depends(db_session)):
        runtime = load_runtime(db, settings)
        if runtime.setup_complete:
            return RedirectResponse("/", status_code=302)
        models_cfg = load_models_config(settings.config_dir)
        connectors_cfg = load_connectors_config(settings.config_dir)
        return templates.TemplateResponse(
            "setup.html",
            ctx(
                request,
                db,
                {
                    "providers": available_providers(include_test=settings.environment == "test"),
                    "models_cfg": models_cfg,
                    "connectors": connector_entries(connectors_cfg),
                },
            ),
        )

    @app.post("/api/setup")
    def api_setup(payload: SetupIn, db: Session = Depends(db_session)):
        complete_setup(
            db,
            settings,
            deployment_name=payload.deployment_name,
            require_login=payload.require_login,
            admin_username=payload.admin_username,
            admin_email=payload.admin_email,
            admin_password=payload.admin_password,
            model_backend=payload.model_backend,
            brand_name=payload.brand_name,
            accent_color=payload.accent_color,
            monthly_cap_usd=payload.monthly_cap_usd,
            connectors=payload.connectors,
            secrets=payload.secrets,
        )
        return {"ok": True, "redirect": "/"}

    @app.post("/setup")
    def setup_form(
        db: Session = Depends(db_session),
        deployment_name: str = Form("ATeam"),
        require_login: str = Form("off"),
        admin_username: str = Form(""),
        admin_email: str = Form(""),
        admin_password: str = Form(""),
        model_backend: str = Form("stub"),
        brand_name: str = Form("ATeam"),
        accent_color: str = Form("#EDAA4B"),
        monthly_cap_usd: float = Form(0),
        email_enabled: str = Form("off"),
        email_mode: str = Form("stub"),
        sms_enabled: str = Form("off"),
        sms_mode: str = Form("stub"),
        anthropic_api_key: str = Form(""),
        postmark_api_token: str = Form(""),
        twilio_account_sid: str = Form(""),
        twilio_auth_token: str = Form(""),
        twilio_from_number: str = Form(""),
    ):
        secrets = {
            "ANTHROPIC_API_KEY": anthropic_api_key,
            "POSTMARK_API_TOKEN": postmark_api_token,
            "TWILIO_ACCOUNT_SID": twilio_account_sid,
            "TWILIO_AUTH_TOKEN": twilio_auth_token,
            "TWILIO_FROM_NUMBER": twilio_from_number,
        }
        complete_setup(
            db,
            settings,
            deployment_name=deployment_name,
            require_login=require_login in {"on", "true", "1"},
            admin_username=admin_username or None,
            admin_email=admin_email or None,
            admin_password=admin_password or None,
            model_backend=model_backend,
            brand_name=brand_name,
            accent_color=accent_color,
            monthly_cap_usd=monthly_cap_usd,
            connectors={
                "email": {"enabled": email_enabled in {"on", "true", "1"}, "mode": email_mode},
                "sms": {"enabled": sms_enabled in {"on", "true", "1"}, "mode": sms_mode},
            },
            secrets=secrets,
        )
        return RedirectResponse("/", status_code=303)

    @app.get("/api/setup/self-test")
    def self_test(db: Session = Depends(db_session)):
        runtime = load_runtime(db, settings)
        checks = []
        health_payload = build_health(db, settings, runtime)
        checks.append({"name": "health", "ok": health_payload.get("app") == "ok"})
        try:
            completion = run_agent(db, settings, runtime, slug="inbox-clerk", prompt="ping")
            checks.append({"name": "stub_agent", "ok": bool(completion.text)})
        except Exception as exc:  # noqa: BLE001 — surface any self-test failure
            checks.append({"name": "stub_agent", "ok": False, "detail": str(exc)})
        ok = all(c["ok"] for c in checks)
        return {"ok": ok, "checks": checks, "green": ok}

    @app.get("/api/providers")
    def list_providers():
        return {"providers": available_providers(include_test=settings.environment == "test")}

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, db: Session = Depends(db_session)):
        runtime = load_runtime(db, settings)
        if runtime.setup_complete and not runtime.require_login:
            return RedirectResponse("/", status_code=302)
        return templates.TemplateResponse("login.html", ctx(request, db))

    @app.post("/api/login")
    def api_login(payload: LoginIn, request: Request, db: Session = Depends(db_session)):
        user = authenticate(db, payload.username, payload.password)
        request.session["user"] = {"id": user.id, "username": user.username, "role": user.role}
        return {"ok": True, "role": user.role}

    @app.post("/login")
    def login_form(
        request: Request,
        db: Session = Depends(db_session),
        username: str = Form(...),
        password: str = Form(...),
    ):
        user = authenticate(db, username, password)
        request.session["user"] = {"id": user.id, "username": user.username, "role": user.role}
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    @app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=302)

    @app.post("/api/password-reset")
    def api_reset(payload: ResetIn, db: Session = Depends(db_session)):
        request_password_reset(db, payload.email)
        return {"ok": True}

    @app.post("/api/password-reset/apply")
    def api_reset_apply(payload: ResetApplyIn, db: Session = Depends(db_session)):
        apply_password_reset(db, payload.token, payload.new_password)
        return {"ok": True}

    @app.get("/api/email-sink")
    def email_sink(request: Request, db: Session = Depends(db_session)):
        require_user(request, db, role="admin")
        rows = db.query(EmailSink).order_by(EmailSink.id.desc()).limit(20).all()
        return {
            "messages": [
                {"to": r.to_addr, "subject": r.subject, "body": r.body} for r in rows
            ]
        }

    @app.get("/api/admin/logs")
    def admin_logs(request: Request, db: Session = Depends(db_session)):
        require_user(request, db, role="admin")
        return list_log_rows(db)

    @app.post("/api/admin/purge-logs")
    def admin_purge_logs(request: Request, db: Session = Depends(db_session)):
        require_user(request, db, role="admin")
        return {"ok": True, **purge_logs(db)}

    def _admin_or_redirect(request: Request, db: Session, settings_only: bool = False):
        runtime = load_runtime(db, settings)
        if not runtime.setup_complete:
            return RedirectResponse("/setup", status_code=302), None
        user = current_user(request, db)
        if runtime.require_login and not user:
            return RedirectResponse("/login", status_code=302), None
        user = user or {"id": 0, "username": "demo", "role": "admin"}
        if settings_only and user.get("role") != "admin":
            return JSONResponse({"detail": "admin only"}, status_code=403), None
        return None, user

    @app.get("/admin", response_class=HTMLResponse)
    def admin_home(request: Request, db: Session = Depends(db_session)):
        redirect, user = _admin_or_redirect(request, db)
        if redirect:
            return redirect
        users = db.query(User).all()
        keys = db.query(ApiKey).all()
        runtime = load_runtime(db, settings)
        capped = is_capped(db, runtime.monthly_cap_usd) if runtime.monthly_cap_usd else False
        extra = {
            "users": users,
            "keys": keys,
            "page": "home",
            "actor": user,
            "spend": month_spend(db),
            "capped": capped,
        }
        return templates.TemplateResponse("admin.html", ctx(request, db, extra))

    @app.get("/admin/settings", response_class=HTMLResponse)
    def admin_settings(request: Request, db: Session = Depends(db_session)):
        redirect, user = _admin_or_redirect(request, db, settings_only=True)
        if redirect:
            return redirect
        runtime = load_runtime(db, settings)
        extra = {
            "page": "settings",
            "actor": user,
            "health": build_health(db, settings, runtime),
        }
        return templates.TemplateResponse("admin_settings.html", ctx(request, db, extra))

    @app.post("/api/admin/users")
    def api_create_user(payload: UserIn, request: Request, db: Session = Depends(db_session)):
        require_user(request, db, role="admin")
        user = create_user(
            db,
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
        return {"ok": True, "id": user.id, "role": user.role}

    @app.post("/api/admin/api-keys")
    def api_create_key(payload: KeyIn, request: Request, db: Session = Depends(db_session)):
        actor = require_user(request, db, role="admin")
        display, row = create_key(db, name=payload.name, created_by=actor["username"])
        return {"ok": True, "key": display, "prefix": row.prefix}

    @app.post("/api/agents/{slug}/messages")
    def agent_message(
        slug: str,
        payload: MessageIn,
        request: Request,
        db: Session = Depends(db_session),
    ):
        runtime = load_runtime(db, settings)
        if not runtime.setup_complete:
            raise HTTPException(status_code=403, detail="complete setup first")
        require_user(request, db)
        result = run_agent(db, settings, runtime, slug=slug, prompt=payload.prompt)
        return {
            "text": result.text,
            "provider": result.provider,
            "fallback": result.fallback,
            "cost_usd": result.cost_usd,
        }

    @app.get("/api/runtime")
    def api_runtime(db: Session = Depends(db_session)):
        runtime = load_runtime(db, settings)
        return {
            "setup_complete": runtime.setup_complete,
            "model_backend": runtime.model_backend,
            "require_login": runtime.require_login,
            "deployment_name": runtime.deployment_name,
            "connectors": runtime.connectors,
            "monthly_cap_usd": runtime.monthly_cap_usd,
        }

    app.state.settings = settings
    app.state.session_factory = factory
    app.state.secret_lookup = lambda db, name: secret_value(db, settings, name)
    return app


# uvicorn app.main:app — skip the default instance under pytest (ENVIRONMENT=test)
if os.environ.get("ENVIRONMENT") != "test":
    app = create_app()
else:
    app = FastAPI(title="ATeam")
