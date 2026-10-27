"""Single source of truth for operational metric definitions.

Every page that shows one of these numbers calls these functions, so a metric is never computed two ways.

Definitions
- Usable stock: batches with status AVAILABLE, screening PASSED, expires_on >= today, at an active organisation.
  Quarantined, reserved, issued, expired, discarded and transferred stock is never usable.
- Registered donors: active (not deactivated/anonymised) donor records.
- Currently available donors: registered donors with consent GRANTED, availability AVAILABLE confirmed within
  ``availability_fresh_days``, and no completed donation within ``whole_blood_deferral_days``. This is an
  operational indicator, not medical eligibility.
- Active requests: requests in a non-terminal status.
- Critical/overdue requests: active requests that are CRITICAL priority or past their required-by time.
- Expiring soon: usable units whose expiry is within ``expiry_warning_days`` (inclusive).
- Fulfilled in period: requests whose status is FULFILLED and whose closed_at falls inside the period.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import BloodBank, BloodRequest, Donor, InventoryBatch
from app.models.enums import (
    AvailabilityStatus,
    BloodGroup,
    ConsentStatus,
    InventoryStatus,
    Provenance,
    RequestPriority,
    RequestStatus,
    ScreeningStatus,
    VerificationStatus,
)
from app.services.lifecycle import OPEN
from app.services.settings import Thresholds


@dataclass
class Filters:
    city: str | None = None
    blood_group: BloodGroup | None = None
    blood_bank_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    request_status: RequestStatus | None = None
    provenance: Provenance | None = None


def today() -> date:
    return datetime.now(UTC).date()


def usable_batch_clause(on: date | None = None):
    on = on or today()
    return and_(
        InventoryBatch.status == InventoryStatus.AVAILABLE,
        InventoryBatch.screening_status == ScreeningStatus.PASSED,
        InventoryBatch.expires_on >= on,
        InventoryBatch.quantity > 0,
        BloodBank.is_active.is_(True),
    )


def usable_batches(f: Filters) -> Select:
    q = select(InventoryBatch).join(BloodBank, BloodBank.id == InventoryBatch.blood_bank_id).where(usable_batch_clause())
    return _filter_inventory(q, f)


def _filter_inventory(q: Select, f: Filters) -> Select:
    if f.city:
        q = q.where(BloodBank.city == f.city)
    if f.blood_group:
        q = q.where(InventoryBatch.blood_group == f.blood_group)
    if f.blood_bank_id:
        q = q.where(InventoryBatch.blood_bank_id == f.blood_bank_id)
    if f.provenance:
        q = q.where(InventoryBatch.provenance == f.provenance)
    return q


def available_donor_clause(t: Thresholds, now: datetime | None = None):
    now = now or datetime.now(UTC)
    return and_(
        Donor.is_active.is_(True),
        Donor.consent_status == ConsentStatus.GRANTED,
        Donor.availability_status == AvailabilityStatus.AVAILABLE,
        Donor.availability_confirmed_at >= now - timedelta(days=t.availability_fresh_days),
        or_(Donor.last_donation_date.is_(None), Donor.last_donation_date <= now.date() - timedelta(days=t.whole_blood_deferral_days)),
    )


def _filter_donors(q: Select, f: Filters) -> Select:
    if f.city:
        q = q.where(Donor.city == f.city)
    if f.blood_group:
        q = q.where(Donor.blood_group == f.blood_group)
    if f.provenance:
        q = q.where(Donor.provenance == f.provenance)
    return q


def _filter_requests(q: Select, f: Filters) -> Select:
    if f.city:
        q = q.where(BloodRequest.city == f.city)
    if f.blood_group:
        q = q.where(BloodRequest.blood_group == f.blood_group)
    if f.blood_bank_id:
        q = q.where(BloodRequest.blood_bank_id == f.blood_bank_id)
    if f.request_status:
        q = q.where(BloodRequest.status == f.request_status)
    if f.provenance:
        q = q.where(BloodRequest.provenance == f.provenance)
    return q


def period_bounds(f: Filters, default_days: int = 30) -> tuple[datetime, datetime]:
    end = f.date_to or today()
    start = f.date_from or (end - timedelta(days=default_days - 1))
    return datetime.combine(start, datetime.min.time(), UTC), datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC)


def kpis(db: Session, f: Filters, t: Thresholds) -> dict:
    now = datetime.now(UTC)
    start, end = period_bounds(f)

    donors_base = _filter_donors(select(func.count(Donor.id)).where(Donor.is_active.is_(True)), f)
    registered = db.scalar(donors_base) or 0
    available = db.scalar(_filter_donors(select(func.count(Donor.id)).where(available_donor_clause(t, now)), f)) or 0

    stock_q = _filter_inventory(
        select(func.coalesce(func.sum(InventoryBatch.quantity), 0))
        .join(BloodBank, BloodBank.id == InventoryBatch.blood_bank_id)
        .where(usable_batch_clause(now.date())),
        f,
    )
    units = db.scalar(stock_q) or 0
    expiring = db.scalar(stock_q.where(InventoryBatch.expires_on <= now.date() + timedelta(days=t.expiry_warning_days))) or 0

    open_q = _filter_requests(select(func.count(BloodRequest.id)).where(BloodRequest.status.in_(OPEN)), f)
    active = db.scalar(open_q) or 0
    critical = db.scalar(open_q.where(or_(BloodRequest.priority == RequestPriority.CRITICAL, BloodRequest.required_by < now))) or 0
    fulfilled = (
        db.scalar(
            _filter_requests(
                select(func.count(BloodRequest.id)).where(
                    BloodRequest.status == RequestStatus.FULFILLED, BloodRequest.closed_at >= start, BloodRequest.closed_at < end
                ),
                f,
            )
        )
        or 0
    )

    banks_q = select(func.count(BloodBank.id)).where(
        BloodBank.is_active.is_(True), BloodBank.verification_status == VerificationStatus.VERIFIED
    )
    if f.city:
        banks_q = banks_q.where(BloodBank.city == f.city)
    if f.provenance:
        banks_q = banks_q.where(BloodBank.provenance == f.provenance)
    verified_banks = db.scalar(banks_q) or 0

    return {
        "registered_donors": registered,
        "available_donors": available,
        "available_units": int(units),
        "active_requests": active,
        "critical_or_overdue_requests": critical,
        "verified_blood_banks": verified_banks,
        "expiring_units": int(expiring),
        "fulfilled_in_period": fulfilled,
        "period_start": start.date().isoformat(),
        "period_end": (end - timedelta(days=1)).date().isoformat(),
    }


def stock_by_group(db: Session, f: Filters) -> dict[str, int]:
    q = _filter_inventory(
        select(InventoryBatch.blood_group, func.sum(InventoryBatch.quantity))
        .join(BloodBank, BloodBank.id == InventoryBatch.blood_bank_id)
        .where(usable_batch_clause())
        .group_by(InventoryBatch.blood_group),
        f,
    )
    result = {g.value: 0 for g in BloodGroup}
    for group, qty in db.execute(q):
        result[BloodGroup(group).value] = int(qty or 0)
    return result
