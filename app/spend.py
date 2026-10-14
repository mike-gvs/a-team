from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import SpendEvent


def month_spend(db: Session) -> float:
    now = datetime.now(timezone.utc)
    total = 0.0
    for event in db.query(SpendEvent).all():
        created = event.created_at
        if created.year == now.year and created.month == now.month:
            total += float(event.amount_usd)
    return round(total, 4)


def record_spend(db: Session, provider: str, amount_usd: float) -> None:
    if amount_usd <= 0:
        return
    db.add(SpendEvent(provider=provider, amount_usd=amount_usd))
    db.commit()


def is_capped(db: Session, monthly_cap_usd: float) -> bool:
    if monthly_cap_usd <= 0:
        # $0 cap means paid providers are off.
        return True
    return month_spend(db) >= monthly_cap_usd
