"""Demo-data seeding with safety guards.

- Refuses to run when BB_ENVIRONMENT=production.
- Refuses to add synthetic data to a database holding imported/verified operational records (unless allow_mixed).
- ``reset`` deletes only rows whose provenance is synthetic and staff accounts flagged ``is_demo``.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    BloodBank,
    BloodRequest,
    ContactAttempt,
    Donation,
    Donor,
    InventoryBatch,
    StockMovement,
    User,
)
from app.models.enums import Provenance
from app.seed.generator import SeedConfig, SeedSummary, generate
from app.seed.validate import validate_dataset

# Deletion order respects foreign keys; dependants (consents, history, match runs, notifications) cascade.
_SYNTHETIC_TABLES = [StockMovement, InventoryBatch, ContactAttempt, Donation, BloodRequest, Donor]
_GUARDED_TABLES = [BloodBank, Donor, BloodRequest, InventoryBatch]


class SeedError(RuntimeError):
    pass


def count_by_provenance(db: Session) -> dict[str, int]:
    counts = {p.value: 0 for p in Provenance}
    for model in _GUARDED_TABLES:
        for prov, n in db.execute(select(model.provenance, func.count()).group_by(model.provenance)):
            counts[Provenance(prov).value] += n
    return counts


def reset_synthetic(db: Session) -> None:
    for model in _SYNTHETIC_TABLES:
        db.execute(delete(model).where(model.provenance == Provenance.SYNTHETIC))
    db.execute(delete(User).where(User.is_demo.is_(True)))
    db.execute(delete(BloodBank).where(BloodBank.provenance == Provenance.SYNTHETIC))


def seed_demo(db: Session, cfg: SeedConfig, *, reset: bool = False, allow_mixed: bool = False) -> SeedSummary:
    if get_settings().environment == "production":
        raise SeedError("Refusing to seed demo data when BB_ENVIRONMENT=production.")
    counts = count_by_provenance(db)
    real = counts["imported"] + counts["verified"]
    if real and not allow_mixed:
        raise SeedError(
            f"The database holds {real} imported/verified records. Synthetic demo data must not be mixed with "
            "operational data; use a separate database (or --allow-mixed for a deliberate test setup)."
        )
    if counts["synthetic"] and not reset:
        raise SeedError("Synthetic demo data already exists. Re-run with --reset to replace it.")
    try:
        if reset:
            reset_synthetic(db)
            db.flush()
        summary = generate(db, cfg)
        problems = validate_dataset(db)
        if problems:
            raise SeedError("Generated data failed consistency checks:\n  " + "\n  ".join(problems[:20]))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return summary
