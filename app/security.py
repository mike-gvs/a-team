from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ROUNDS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, rounds_s, salt, digest = stored.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds_s))
    return hmac.compare_digest(derived.hex(), digest)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_api_key() -> tuple[str, str, str]:
    """Return (display_key, prefix, hash)."""
    secret = secrets.token_urlsafe(24)
    display = f"atk_{secret}"
    prefix = display[:12]
    return display, prefix, hash_token(display)


def new_reset_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)
