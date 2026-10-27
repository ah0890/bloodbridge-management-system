from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models import BloodBank
from app.models.enums import Provenance

router = APIRouter(prefix="/meta", tags=["meta"])

# Tables carrying a provenance column. Extended as models are added.
PROVENANCE_MODELS: list = [BloodBank]


@router.get("/data-status")
def data_status(db: DbSession) -> dict:
    """Public, aggregate-only counts used to label demo environments. Contains no record contents."""
    counts = {p: 0 for p in Provenance}
    for model in PROVENANCE_MODELS:
        for prov, n in db.execute(select(model.provenance, func.count()).group_by(model.provenance)):
            counts[Provenance(prov)] += n
    return {
        "synthetic_records": counts[Provenance.SYNTHETIC],
        "imported_records": counts[Provenance.IMPORTED],
        "verified_records": counts[Provenance.VERIFIED],
        "demo_mode": counts[Provenance.SYNTHETIC] > 0,
    }
