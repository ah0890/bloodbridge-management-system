from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession, org_scope
from app.core.permissions import Perm, has_perm
from app.models import BloodBank, BloodRequest, Donor

router = APIRouter(tags=["search"])


@router.get("/search")
def search(db: DbSession, user: CurrentUser, q: str = Query(min_length=2, max_length=100)) -> dict:
    """Search across entities the user may see. Results contain identifiers only, never contact details."""
    term = f"%{q.strip().lower()}%"
    out: dict[str, list[dict]] = {"donors": [], "requests": [], "blood_banks": []}

    if has_perm(user.role, Perm.DONORS_READ):
        for d in db.scalars(
            select(Donor)
            .where(or_(func.lower(Donor.code).like(term), func.lower(Donor.display_name).like(term)))
            .order_by(Donor.code)
            .limit(8)
        ):
            out["donors"].append(
                {
                    "id": d.id,
                    "code": d.code,
                    "label": d.display_name,
                    "meta": f"{d.blood_group.value} · {d.city}",
                    "provenance": d.provenance,
                }
            )

    if has_perm(user.role, Perm.REQUESTS_READ):
        stmt = select(BloodRequest).where(
            or_(
                func.lower(BloodRequest.code).like(term),
                func.lower(BloodRequest.hospital_name).like(term),
                func.lower(BloodRequest.city).like(term),
            )
        )
        if (scope := org_scope(user)) is not None:
            stmt = stmt.where(BloodRequest.blood_bank_id == scope)
        for r in db.scalars(stmt.order_by(BloodRequest.submitted_at.desc()).limit(8)):
            out["requests"].append(
                {
                    "id": r.id,
                    "code": r.code,
                    "label": f"{r.units_required} × {r.blood_group.value}",
                    "meta": f"{r.city} · {r.status.value.replace('_', ' ')}",
                    "provenance": r.provenance,
                }
            )

    if has_perm(user.role, Perm.BANKS_READ):
        for b in db.scalars(
            select(BloodBank)
            .where(or_(func.lower(BloodBank.code).like(term), func.lower(BloodBank.name).like(term), func.lower(BloodBank.city).like(term)))
            .order_by(BloodBank.name)
            .limit(8)
        ):
            out["blood_banks"].append({"id": b.id, "code": b.code, "label": b.name, "meta": b.city, "provenance": b.provenance})
    return out
