from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select

from app.api.deps import DbSession, client_ip, record_provenance, require
from app.core.permissions import Perm, has_perm
from app.db.base import utcnow
from app.models import BloodRequest, ContactAttempt, Donor, DonorAvailabilityChange, DonorConsent, User
from app.models.enums import (
    AvailabilityStatus,
    BloodGroup,
    ConsentStatus,
    ContactOutcome,
    DonorVerification,
    Provenance,
    Role,
)
from app.schemas.common import Page
from app.schemas.donor import (
    AvailabilityUpdate,
    ConsentUpdate,
    ContactAttemptCreate,
    ContactAttemptOut,
    DonorCreate,
    DonorDetail,
    DonorListItem,
    DonorUpdate,
    _age_on,
)
from app.services import audit
from app.services.csv_export import csv_response
from app.services.metrics import available_donor_clause
from app.services.settings import get_thresholds

router = APIRouter(prefix="/donors", tags=["donors"])

Reader = Annotated[User, Depends(require(Perm.DONORS_READ))]
Writer = Annotated[User, Depends(require(Perm.DONORS_WRITE))]
Contactor = Annotated[User, Depends(require(Perm.DONORS_CONTACT))]

SORTS = {
    "registered_at": Donor.registered_at,
    "display_name": Donor.display_name,
    "code": Donor.code,
    "city": Donor.city,
    "availability_confirmed_at": Donor.availability_confirmed_at,
    "last_donation_date": Donor.last_donation_date,
}


def _get(db, donor_id: int) -> Donor:
    donor = db.get(Donor, donor_id)
    if donor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found.")
    return donor


def _filtered(
    q: str | None,
    blood_group: BloodGroup | None,
    city: str | None,
    consent: ConsentStatus | None,
    verification: DonorVerification | None,
    availability: AvailabilityStatus | None,
    provenance: Provenance | None,
    active: bool | None,
):
    stmt = select(Donor)
    if q:
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(func.lower(Donor.code).like(term), func.lower(Donor.display_name).like(term), func.lower(Donor.city).like(term))
        )
    for col, val in (
        (Donor.blood_group, blood_group),
        (Donor.city, city),
        (Donor.consent_status, consent),
        (Donor.verification_status, verification),
        (Donor.availability_status, availability),
        (Donor.provenance, provenance),
        (Donor.is_active, active),
    ):
        if val is not None:
            stmt = stmt.where(col == val)
    return stmt


@router.get("", response_model=Page[DonorListItem])
def list_donors(
    db: DbSession,
    user: Reader,
    q: str | None = Query(None, max_length=100),
    blood_group: BloodGroup | None = None,
    city: str | None = None,
    consent: ConsentStatus | None = None,
    verification: DonorVerification | None = None,
    availability: AvailabilityStatus | None = None,
    provenance: Provenance | None = None,
    active: Literal["true", "false", "all"] = "true",
    currently_available: bool | None = None,
    sort: str = Query("registered_at", pattern="^(" + "|".join(SORTS) + ")$"),
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> Page[DonorListItem]:
    t = get_thresholds(db)
    clause = available_donor_clause(t)
    stmt = _filtered(q, blood_group, city, consent, verification, availability, provenance, None if active == "all" else active == "true")
    if currently_available is True:
        stmt = stmt.where(clause)
    elif currently_available is False:
        stmt = stmt.where(~clause)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    col = SORTS[sort]
    rows = db.execute(
        stmt.add_columns(clause.label("ca"))
        .order_by(col.desc() if order == "desc" else col.asc(), Donor.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = []
    for donor, ca in rows:
        item = DonorListItem.model_validate(donor)
        item.currently_available = bool(ca)
        items.append(item)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/cities", response_model=list[str])
def donor_cities(db: DbSession, user: Reader) -> list[str]:
    return list(db.scalars(select(Donor.city).distinct().order_by(Donor.city)))


@router.get("/export.csv")
def export_donors(
    request: Request,
    db: DbSession,
    user: Annotated[User, Depends(require(Perm.DONORS_EXPORT))],
    blood_group: BloodGroup | None = None,
    city: str | None = None,
    availability: AvailabilityStatus | None = None,
    provenance: Provenance | None = None,
) -> StreamingResponse:
    """Minimised export: no contact details, date of birth, coordinates or notes."""
    stmt = _filtered(None, blood_group, city, None, None, availability, provenance, True).order_by(Donor.code)
    rows = [
        [
            d.code,
            d.display_name,
            d.blood_group.value,
            d.city,
            d.availability_status.value,
            d.consent_status.value,
            d.verification_status.value,
            d.last_donation_date,
            d.provenance.value,
        ]
        for d in db.scalars(stmt)
    ]
    audit.record(
        db,
        actor=user,
        action="donors.export",
        entity_type="donor",
        summary=f"Exported {len(rows)} donor rows (minimised fields)",
        details={"filters": {"blood_group": blood_group, "city": city, "availability": availability, "provenance": provenance}},
        ip=client_ip(request),
    )
    db.commit()
    header = [
        "donor_id",
        "display_name",
        "blood_group",
        "city",
        "availability",
        "consent",
        "verification",
        "last_donation_date",
        "provenance",
    ]
    return csv_response("donors.csv", header, rows, synthetic=any(r[-1] == "synthetic" for r in rows))


def _detail(db, donor: Donor, viewer: User) -> DonorDetail:
    t = get_thresholds(db)
    detail = DonorDetail.model_validate(donor)
    detail.currently_available = bool(db.scalar(select(available_donor_clause(t)).where(Donor.id == donor.id)))
    detail.age = _age_on(donor.date_of_birth, datetime.now(UTC).date()) if donor.date_of_birth else None
    detail.contact_attempts = [
        ContactAttemptOut.model_validate(c)
        for c in db.scalars(select(ContactAttempt).where(ContactAttempt.donor_id == donor.id).order_by(ContactAttempt.attempted_at.desc()))
    ]
    if not has_perm(viewer.role, Perm.DONORS_CONTACT):
        detail.phone = detail.email = detail.staff_notes = None
    return detail


@router.get("/{donor_id}", response_model=DonorDetail)
def get_donor(donor_id: int, request: Request, db: DbSession, user: Reader) -> DonorDetail:
    donor = _get(db, donor_id)
    if has_perm(user.role, Perm.DONORS_CONTACT) and donor.phone:
        audit.record(
            db,
            actor=user,
            action="donors.view_contact",
            entity_type="donor",
            entity_id=donor.code,
            summary=f"Viewed contact details of {donor.code}",
            ip=client_ip(request),
        )
        db.commit()
    return _detail(db, donor, user)


@router.post("", response_model=DonorDetail, status_code=status.HTTP_201_CREATED)
def create_donor(body: DonorCreate, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    now = utcnow()
    next_num = (db.scalar(select(func.max(Donor.id))) or 0) + 1
    data = body.model_dump(exclude={"consent_confirmed", "consent_method", "availability_status"})
    donor = Donor(
        **data,
        code=f"DNR-{next_num:06d}",
        consent_status=ConsentStatus.GRANTED,
        consent_at=now,
        availability_status=body.availability_status,
        availability_confirmed_at=now if body.availability_status != AvailabilityStatus.UNKNOWN else None,
        registered_at=now,
        provenance=record_provenance(user),
        created_by_id=user.id,
    )
    db.add(donor)
    db.flush()
    db.add(
        DonorConsent(donor_id=donor.id, status=ConsentStatus.GRANTED, method=body.consent_method, recorded_at=now, recorded_by_id=user.id)
    )
    db.add(
        DonorAvailabilityChange(
            donor_id=donor.id,
            from_status=None,
            to_status=body.availability_status,
            changed_at=now,
            changed_by_id=user.id,
            source="registration",
        )
    )
    audit.record(
        db,
        actor=user,
        action="donors.create",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"Registered donor {donor.code} ({donor.blood_group.value}, {donor.city})",
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)


@router.patch("/{donor_id}", response_model=DonorDetail)
def update_donor(donor_id: int, body: DonorUpdate, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    donor = _get(db, donor_id)
    if donor.anonymized_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Anonymised donor records cannot be edited.")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(donor, key, value)
    if donor.preferred_contact.value == "email" and not donor.email:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "An email address is required when email is the preferred contact method."
        )
    if donor.preferred_contact.value != "email" and not donor.phone:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A phone number is required for phone, SMS or WhatsApp contact.")
    # Field names only: values may be personal data.
    audit.record(
        db,
        actor=user,
        action="donors.update",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"Updated donor {donor.code}",
        details={"fields": sorted(changes)},
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)


@router.post("/{donor_id}/availability", response_model=DonorDetail)
def set_availability(donor_id: int, body: AvailabilityUpdate, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    donor = _get(db, donor_id)
    if not donor.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Donor record is inactive.")
    if body.status == AvailabilityStatus.AVAILABLE and donor.consent_status != ConsentStatus.GRANTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "A donor without current consent cannot be marked available.")
    now = utcnow()
    db.add(
        DonorAvailabilityChange(
            donor_id=donor.id,
            from_status=donor.availability_status,
            to_status=body.status,
            changed_at=now,
            changed_by_id=user.id,
            source=body.source,
            note=body.note,
        )
    )
    previous = donor.availability_status
    donor.availability_status = body.status
    donor.availability_confirmed_at = now
    audit.record(
        db,
        actor=user,
        action="donors.availability",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"{donor.code} availability {previous.value} → {body.status.value}",
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)


@router.post("/{donor_id}/consent", response_model=DonorDetail)
def set_consent(donor_id: int, body: ConsentUpdate, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    donor = _get(db, donor_id)
    now = utcnow()
    db.add(DonorConsent(donor_id=donor.id, status=body.status, method=body.method, recorded_at=now, recorded_by_id=user.id))
    donor.consent_status, donor.consent_at = body.status, now
    if body.status == ConsentStatus.WITHDRAWN and donor.availability_status != AvailabilityStatus.UNAVAILABLE:
        db.add(
            DonorAvailabilityChange(
                donor_id=donor.id,
                from_status=donor.availability_status,
                to_status=AvailabilityStatus.UNAVAILABLE,
                changed_at=now,
                changed_by_id=user.id,
                source="staff_review",
                note="Consent withdrawn",
            )
        )
        donor.availability_status, donor.availability_confirmed_at = AvailabilityStatus.UNAVAILABLE, now
    audit.record(
        db,
        actor=user,
        action="donors.consent",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"{donor.code} consent {body.status.value} ({body.method})",
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)


@router.post("/{donor_id}/contact-attempts", response_model=ContactAttemptOut, status_code=status.HTTP_201_CREATED)
def record_contact(donor_id: int, body: ContactAttemptCreate, request: Request, db: DbSession, user: Contactor) -> ContactAttemptOut:
    """Record an attempt made outside BloodBridge. BloodBridge itself never sends messages."""
    donor = _get(db, donor_id)
    if donor.consent_status != ConsentStatus.GRANTED:
        raise HTTPException(status.HTTP_409_CONFLICT, "This donor has not consented to be contacted.")
    if not donor.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Donor record is inactive.")
    if body.request_id is not None and db.get(BloodRequest, body.request_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Referenced request does not exist.")
    attempt = ContactAttempt(
        donor_id=donor.id,
        request_id=body.request_id,
        coordinator_id=user.id,
        attempted_at=utcnow(),
        method=body.method,
        outcome=body.outcome,
        notes=body.notes,
        provenance=Provenance.SYNTHETIC if donor.provenance == Provenance.SYNTHETIC else record_provenance(user),
    )
    db.add(attempt)
    if body.outcome == ContactOutcome.NOT_ELIGIBLE and donor.availability_status == AvailabilityStatus.AVAILABLE:
        db.add(
            DonorAvailabilityChange(
                donor_id=donor.id,
                from_status=donor.availability_status,
                to_status=AvailabilityStatus.TEMPORARILY_DEFERRED,
                changed_at=utcnow(),
                changed_by_id=user.id,
                source="contact_attempt",
                note="Donor reported not eligible",
            )
        )
        donor.availability_status, donor.availability_confirmed_at = AvailabilityStatus.TEMPORARILY_DEFERRED, utcnow()
    db.flush()
    audit.record(
        db,
        actor=user,
        action="donors.contact_attempt",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"Recorded {body.method.value} contact with {donor.code}: {body.outcome.value}",
        details={"request_id": body.request_id},
        ip=client_ip(request),
    )
    db.commit()
    return ContactAttemptOut.model_validate(attempt)


@router.post("/{donor_id}/deactivate", response_model=DonorDetail)
def deactivate(donor_id: int, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    donor = _get(db, donor_id)
    donor.is_active = False
    audit.record(
        db,
        actor=user,
        action="donors.deactivate",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"Deactivated donor {donor.code}",
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)


@router.post("/{donor_id}/reactivate", response_model=DonorDetail)
def reactivate(donor_id: int, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    donor = _get(db, donor_id)
    if donor.anonymized_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Anonymised donor records cannot be reactivated.")
    donor.is_active = True
    audit.record(
        db,
        actor=user,
        action="donors.reactivate",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"Reactivated donor {donor.code}",
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)


@router.post("/{donor_id}/anonymize", response_model=DonorDetail)
def anonymize(donor_id: int, request: Request, db: DbSession, user: Writer) -> DonorDetail:
    """Irreversibly strip personal data while keeping aggregate history (donations, blood group, city)."""
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only platform administrators can anonymise donor records.")
    donor = _get(db, donor_id)
    if donor.anonymized_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Donor is already anonymised.")
    now = utcnow()
    donor.display_name = f"Anonymised donor {donor.code}"
    donor.phone = donor.email = donor.staff_notes = donor.locality = None
    donor.date_of_birth = None
    donor.latitude = donor.longitude = None
    donor.is_active = False
    donor.consent_status = ConsentStatus.WITHDRAWN
    donor.availability_status = AvailabilityStatus.UNAVAILABLE
    donor.anonymized_at = now
    db.add(DonorConsent(donor_id=donor.id, status=ConsentStatus.WITHDRAWN, method="in_person", recorded_at=now, recorded_by_id=user.id))
    for attempt in db.scalars(select(ContactAttempt).where(ContactAttempt.donor_id == donor.id)):
        attempt.notes = None
    audit.record(
        db,
        actor=user,
        action="donors.anonymize",
        entity_type="donor",
        entity_id=donor.code,
        summary=f"Anonymised donor {donor.code}",
        ip=client_ip(request),
    )
    db.commit()
    return _detail(db, donor, user)
