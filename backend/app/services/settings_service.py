from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Setting

DEFAULTS: dict[str, float] = {
    "drift_share_threshold": 0.3,   # share of drifted features that counts as dataset drift
    "min_current_rows": 50,         # minimum logged predictions needed to run drift detection
    "monitoring_window": 1000,      # most recent predictions used as the "current" dataset
    "min_roc_auc": 0.7,             # absolute floor a candidate must reach to be promoted
    "min_improvement": 0.0,         # candidate must beat champion by this much on F1 and ROC-AUC (negative = tolerance)
    "schedule_hours": 0,            # scheduled retraining interval in hours (0 = disabled)
}
LIMITS = {
    "drift_share_threshold": (0.01, 1.0), "min_current_rows": (10, 100000), "monitoring_window": (10, 100000),
    "min_roc_auc": (0.5, 1.0), "min_improvement": (-0.2, 0.2), "schedule_hours": (0, 24 * 365),
}


def get_all(db: Session) -> dict[str, float]:
    values = dict(DEFAULTS)
    for row in db.query(Setting).all():
        if row.key in DEFAULTS:
            values[row.key] = float(row.value)
    return values


def update(db: Session, new: dict[str, float]) -> dict[str, float]:
    for key, value in new.items():
        if key not in DEFAULTS:
            raise ValueError(f"Unknown setting: {key}")
        lo, hi = LIMITS[key]
        if not lo <= float(value) <= hi:
            raise ValueError(f"{key} must be between {lo} and {hi}")
        row = db.get(Setting, key)
        if row:
            row.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    return get_all(db)
