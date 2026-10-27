from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select

from app.api.deps import DbSession, org_scope, require
from app.core.permissions import Perm
from app.models import BloodBank, BloodRequest, Donor, DonorAvailabilityChange, InventoryBatch, RequestStatusChange, StockMovement, User
from app.models.enums import BloodGroup, InventoryStatus, Provenance, RequestPriority, RequestStatus
from app.services import metrics
from app.services.lifecycle import OPEN
from app.services.metrics import Filters
from app.services.settings import get_thresholds

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

Viewer = Annotated[User, Depends(require(Perm.DASHBOARD_VIEW))]


def dashboard_filters(
    user: Viewer,
    city: str | None = None,
    blood_group: BloodGroup | None = None,
    blood_bank_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    request_status: RequestStatus | None = None,
    provenance: Provenance | None = None,
) -> Filters:
    # Bank managers always see their own organisation's operational data.
    scope = org_scope(user)
    return Filters(city, blood_group, scope or blood_bank_id, date_from, date_to, request_status, provenance)


DashFilters = Annotated[Filters, Depends(dashboard_filters)]


@router.get("/summary")
def summary(db: DbSession, user: Viewer, f: DashFilters) -> dict:
    t = get_thresholds(db)
    return {
        "kpis": metrics.kpis(db, f, t),
        "stock_by_group": metrics.stock_by_group(db, f),
        "thresholds": t.__dict__,
        "scope": {"blood_bank_id": f.blood_bank_id, "org_scoped": org_scope(user) is not None},
    }


@router.get("/inventory-health")
def inventory_health(db: DbSession, user: Viewer, f: DashFilters) -> dict:
    t = get_thresholds(db)
    today = metrics.today()
    by_group = metrics.stock_by_group(db, f)
    low = [{"blood_group": g, "units": u, "threshold": t.low_stock_units} for g, u in by_group.items() if u < t.low_stock_units]

    expiring = db.execute(
        metrics.usable_batches(f)
        .where(InventoryBatch.expires_on <= today + timedelta(days=t.expiry_warning_days))
        .order_by(InventoryBatch.expires_on, InventoryBatch.id)
        .limit(12)
        .add_columns(BloodBank.name, BloodBank.city)
    ).all()

    # Stock excluded from usable totals, by reason.
    excl = (
        select(
            case(
                (InventoryBatch.status == InventoryStatus.QUARANTINED, "quarantined"),
                (InventoryBatch.status == InventoryStatus.RESERVED, "reserved"),
                ((InventoryBatch.status == InventoryStatus.AVAILABLE) & (InventoryBatch.expires_on < today), "expired_not_yet_written_off"),
                else_="other",
            ).label("reason"),
            func.sum(InventoryBatch.quantity),
        )
        .join(BloodBank, BloodBank.id == InventoryBatch.blood_bank_id)
        .where(
            (InventoryBatch.status.in_([InventoryStatus.QUARANTINED, InventoryStatus.RESERVED]))
            | ((InventoryBatch.status == InventoryStatus.AVAILABLE) & (InventoryBatch.expires_on < today))
        )
        .group_by("reason")
    )
    excl = metrics._filter_inventory(excl, f)
    excluded = {r: int(q or 0) for r, q in db.execute(excl)}
    expired_30 = metrics._filter_inventory(
        select(func.coalesce(func.sum(StockMovement.quantity), 0))
        .select_from(StockMovement)
        .join(InventoryBatch, InventoryBatch.id == StockMovement.batch_id)
        .join(BloodBank, BloodBank.id == StockMovement.blood_bank_id)
        .where(
            StockMovement.movement_type.in_(["expired", "discarded"]), StockMovement.occurred_at >= datetime.now(UTC) - timedelta(days=30)
        ),
        f,
    )

    movements = db.execute(
        metrics._filter_inventory(
            select(StockMovement, InventoryBatch.code, InventoryBatch.blood_group, InventoryBatch.component, BloodBank.name)
            .join(InventoryBatch, InventoryBatch.id == StockMovement.batch_id)
            .join(BloodBank, BloodBank.id == StockMovement.blood_bank_id),
            f,
        )
        .order_by(StockMovement.occurred_at.desc())
        .limit(10)
    ).all()

    return {
        "low_stock": low,
        "expiring": [
            {
                "id": b.id,
                "code": b.code,
                "blood_group": b.blood_group,
                "component": b.component,
                "quantity": b.quantity,
                "expires_on": b.expires_on,
                "blood_bank": name,
                "city": city,
                "provenance": b.provenance,
            }
            for b, name, city in expiring
        ],
        "excluded_units": excluded,
        "wasted_last_30_days": int(db.scalar(expired_30) or 0),
        "recent_movements": [
            {
                "id": m.id,
                "type": m.movement_type,
                "quantity": m.quantity,
                "occurred_at": m.occurred_at,
                "batch_code": code,
                "blood_group": group,
                "component": comp,
                "blood_bank": bank,
                "provenance": m.provenance,
            }
            for m, code, group, comp, bank in movements
        ],
    }


@router.get("/requests")
def request_activity(db: DbSession, user: Viewer, f: DashFilters, days: int = Query(30, ge=7, le=365)) -> dict:
    start, end = metrics.period_bounds(f, default_days=days)
    base = metrics._filter_requests(select(BloodRequest), f)

    received = dict(
        db.execute(
            metrics._filter_requests(
                select(func.date(BloodRequest.submitted_at), func.count())
                .where(BloodRequest.submitted_at >= start, BloodRequest.submitted_at < end)
                .group_by(func.date(BloodRequest.submitted_at)),
                f,
            )
        ).all()
    )
    fulfilled = dict(
        db.execute(
            metrics._filter_requests(
                select(func.date(BloodRequest.closed_at), func.count())
                .where(BloodRequest.status == RequestStatus.FULFILLED, BloodRequest.closed_at >= start, BloodRequest.closed_at < end)
                .group_by(func.date(BloodRequest.closed_at)),
                f,
            )
        ).all()
    )
    series = []
    d = start.date()
    while d < end.date():
        key = d.isoformat()
        series.append({"date": key, "received": received.get(key, 0), "fulfilled": fulfilled.get(key, 0)})
        d += timedelta(days=1)

    by_status = {s.value: 0 for s in RequestStatus}
    for s, n in db.execute(metrics._filter_requests(select(BloodRequest.status, func.count()).group_by(BloodRequest.status), f)):
        by_status[RequestStatus(s).value] = n
    by_priority = {p.value: 0 for p in RequestPriority}
    for p, n in db.execute(
        metrics._filter_requests(
            select(BloodRequest.priority, func.count()).where(BloodRequest.status.in_(OPEN)).group_by(BloodRequest.priority), f
        )
    ):
        by_priority[RequestPriority(p).value] = n

    def brief(r: BloodRequest) -> dict:
        return {
            "id": r.id,
            "code": r.code,
            "blood_group": r.blood_group,
            "component": r.component,
            "units_required": r.units_required,
            "units_fulfilled": r.units_fulfilled,
            "city": r.city,
            "priority": r.priority,
            "status": r.status,
            "required_by": r.required_by,
            "submitted_at": r.submitted_at,
            "provenance": r.provenance,
        }

    awaiting = db.scalars(
        base.where(BloodRequest.status.in_([RequestStatus.SUBMITTED, RequestStatus.UNDER_REVIEW, RequestStatus.MATCHES_FOUND]))
        .order_by(BloodRequest.required_by)
        .limit(8)
    ).all()
    emergencies = db.scalars(
        base.where(BloodRequest.priority == RequestPriority.CRITICAL).order_by(BloodRequest.submitted_at.desc()).limit(8)
    ).all()
    return {
        "series": series,
        "by_status": by_status,
        "open_total": sum(v for k, v in by_status.items() if RequestStatus(k) in OPEN),
        "closed_total": sum(v for k, v in by_status.items() if RequestStatus(k) not in OPEN),
        "open_by_priority": by_priority,
        "awaiting_coordination": [brief(r) for r in awaiting],
        "recent_emergencies": [brief(r) for r in emergencies],
    }


@router.get("/activity")
def activity(db: DbSession, user: Viewer, f: DashFilters, limit: int = Query(25, ge=5, le=100)) -> list[dict]:
    """Chronological feed assembled from source tables. Donors are referenced by ID only."""
    events: list[dict] = []
    req_q = (
        select(RequestStatusChange, BloodRequest.code, BloodRequest.provenance)
        .join(BloodRequest, BloodRequest.id == RequestStatusChange.request_id)
        .order_by(RequestStatusChange.changed_at.desc())
        .limit(limit)
    )
    for ch, code, prov in db.execute(metrics._filter_requests(req_q, f)):
        kind = "request_created" if ch.from_status is None else "request_status"
        text = (
            f"{code} submitted"
            if ch.from_status is None
            else f"{code}: {ch.from_status.value.replace('_', ' ')} → {ch.to_status.value.replace('_', ' ')}"
        )
        events.append({"at": ch.changed_at, "kind": kind, "text": text, "link": f"/requests/{ch.request_id}", "provenance": prov})

    mv_q = (
        metrics._filter_inventory(
            select(StockMovement, InventoryBatch.code, InventoryBatch.blood_group, BloodBank.name)
            .join(InventoryBatch, InventoryBatch.id == StockMovement.batch_id)
            .join(BloodBank, BloodBank.id == StockMovement.blood_bank_id)
            .where(StockMovement.movement_type.in_(["received", "issued", "transfer_in", "expired", "discarded"])),
            f,
        )
        .order_by(StockMovement.occurred_at.desc())
        .limit(limit)
    )
    for m, _code, group, bank in db.execute(mv_q):
        events.append(
            {
                "at": m.occurred_at,
                "kind": f"stock_{m.movement_type.value}",
                "text": f"{m.quantity} × {group.value} {m.movement_type.value.replace('_', ' ')} · {bank}",
                "link": f"/inventory/{m.batch_id}",
                "provenance": m.provenance,
            }
        )

    if f.blood_bank_id is None:
        av_q = (
            select(DonorAvailabilityChange, Donor.code, Donor.blood_group, Donor.provenance)
            .join(Donor, Donor.id == DonorAvailabilityChange.donor_id)
            .where(DonorAvailabilityChange.from_status.is_not(None))
        )
        if f.city:
            av_q = av_q.where(Donor.city == f.city)
        if f.blood_group:
            av_q = av_q.where(Donor.blood_group == f.blood_group)
        for ch, code, group, prov in db.execute(av_q.order_by(DonorAvailabilityChange.changed_at.desc()).limit(limit)):
            events.append(
                {
                    "at": ch.changed_at,
                    "kind": "donor_availability",
                    "text": f"Donor {code} ({group.value}) availability → {ch.to_status.value.replace('_', ' ')}",
                    "link": f"/donors/{ch.donor_id}",
                    "provenance": prov,
                }
            )

        bank_q = select(BloodBank).where(BloodBank.last_verified_at.is_not(None))
        if f.city:
            bank_q = bank_q.where(BloodBank.city == f.city)
        for b in db.scalars(bank_q.order_by(BloodBank.last_verified_at.desc()).limit(5)):
            events.append(
                {
                    "at": b.last_verified_at,
                    "kind": "bank_verified",
                    "text": f"{b.name} verification confirmed",
                    "link": f"/blood-banks/{b.id}",
                    "provenance": b.provenance,
                }
            )

    events.sort(key=lambda e: e["at"], reverse=True)
    return events[:limit]


@router.get("/cities")
def city_overview(db: DbSession, user: Viewer, f: DashFilters) -> list[dict]:
    """City-level supply/demand. Donor counts are aggregates only."""
    t = get_thresholds(db)
    f_nocity = Filters(None, f.blood_group, f.blood_bank_id, f.date_from, f.date_to, None, f.provenance)
    banks = dict(
        db.execute(
            select(BloodBank.city, func.count())
            .where(BloodBank.is_active.is_(True), BloodBank.verification_status == "verified")
            .group_by(BloodBank.city)
        ).all()
    )
    stock: dict[str, dict[str, int]] = {}
    for city, group, qty in db.execute(
        metrics._filter_inventory(
            select(BloodBank.city, InventoryBatch.blood_group, func.sum(InventoryBatch.quantity))
            .join(BloodBank, BloodBank.id == InventoryBatch.blood_bank_id)
            .where(metrics.usable_batch_clause())
            .group_by(BloodBank.city, InventoryBatch.blood_group),
            f_nocity,
        )
    ):
        stock.setdefault(city, {g.value: 0 for g in BloodGroup})[BloodGroup(group).value] = int(qty)
    open_req = dict(
        db.execute(
            metrics._filter_requests(
                select(BloodRequest.city, func.count()).where(BloodRequest.status.in_(OPEN)).group_by(BloodRequest.city), f_nocity
            )
        ).all()
    )
    donors = dict(
        db.execute(
            metrics._filter_donors(select(Donor.city, func.count()).where(metrics.available_donor_clause(t)).group_by(Donor.city), f_nocity)
        ).all()
    )
    cities = sorted(set(banks) | set(stock) | set(open_req) | set(donors))
    rows = []
    for c in cities:
        units = sum(stock.get(c, {}).values())
        rows.append(
            {
                "city": c,
                "verified_banks": banks.get(c, 0),
                "available_units": units,
                "stock_by_group": stock.get(c, {g.value: 0 for g in BloodGroup}),
                "open_requests": open_req.get(c, 0),
                "available_donors": donors.get(c, 0),
                "coverage_gap": banks.get(c, 0) == 0 or (open_req.get(c, 0) > 0 and units == 0),
            }
        )
    return rows
