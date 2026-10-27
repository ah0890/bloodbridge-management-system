"""Operational thresholds: environment defaults, overridable by administrators via the app_settings table."""

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppSetting


@dataclass(frozen=True)
class Thresholds:
    low_stock_units: int
    expiry_warning_days: int
    availability_fresh_days: int
    whole_blood_deferral_days: int


# key -> (minimum, maximum) accepted values
LIMITS: dict[str, tuple[int, int]] = {
    "low_stock_units": (0, 1000),
    "expiry_warning_days": (1, 60),
    "availability_fresh_days": (7, 365),
    "whole_blood_deferral_days": (56, 365),
}


def defaults() -> Thresholds:
    s = get_settings()
    return Thresholds(s.low_stock_units, s.expiry_warning_days, s.availability_fresh_days, s.whole_blood_deferral_days)


def get_thresholds(db: Session) -> Thresholds:
    values = asdict(defaults())
    for row in db.scalars(select(AppSetting).where(AppSetting.key.in_(LIMITS))):
        if isinstance(row.value, int):
            values[row.key] = row.value
    return Thresholds(**values)
