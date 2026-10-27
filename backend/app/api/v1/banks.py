from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import DbSession, require
from app.core.permissions import Perm
from app.models import BloodBank, User
from app.models.enums import OrgType, Provenance, VerificationStatus

router = APIRouter(prefix="/blood-banks", tags=["blood banks"])

Reader = Annotated[User, Depends(require(Perm.BANKS_READ))]


class BloodBankOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    org_type: OrgType
    city: str
    address: str | None
    phone: str | None
    email: str | None
    operating_hours: str | None
    supported_components: list[str]
    verification_status: VerificationStatus
    provenance: Provenance
    source_reference: str | None
    last_verified_at: datetime | None
    inventory_updated_at: datetime | None
    is_active: bool


@router.get("", response_model=list[BloodBankOut])
def list_banks(db: DbSession, user: Reader, city: str | None = None, active: bool | None = None) -> list[BloodBank]:
    stmt = select(BloodBank).order_by(BloodBank.city, BloodBank.name)
    if city:
        stmt = stmt.where(BloodBank.city == city)
    if active is not None:
        stmt = stmt.where(BloodBank.is_active.is_(active))
    return list(db.scalars(stmt))


@router.get("/cities", response_model=list[str])
def bank_cities(db: DbSession, user: Reader) -> list[str]:
    return list(db.scalars(select(BloodBank.city).distinct().order_by(BloodBank.city)))


@router.get("/{bank_id}", response_model=BloodBankOut)
def get_bank(bank_id: int, db: DbSession, user: Reader) -> BloodBank:
    bank = db.get(BloodBank, bank_id)
    if bank is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood bank not found.")
    return bank
