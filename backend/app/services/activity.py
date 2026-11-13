from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import ActivityLog


def log(db: Session, event: str, message: str) -> None:
    db.add(ActivityLog(event=event, message=message))
    db.commit()
