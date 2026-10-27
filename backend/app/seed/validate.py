"""Cross-table consistency checks. Used after seeding, by tests, and available via ``python -m app.cli validate-data``."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BloodRequest, Donation, Donor, InventoryBatch, RequestStatusChange, StockMovement
from app.models.enums import ConsentStatus, DonationStatus, InventoryStatus, MovementType, ScreeningStatus
from app.services.compatibility import compatible_donor_groups
from app.services.lifecycle import TERMINAL, can_transition


def validate_dataset(db: Session) -> list[str]:
    problems: list[str] = []

    # Usable stock must be released, in date and positive.
    bad_available = db.scalars(
        select(InventoryBatch).where(
            InventoryBatch.status == InventoryStatus.AVAILABLE,
            (InventoryBatch.screening_status != ScreeningStatus.PASSED) | (InventoryBatch.quantity <= 0),
        )
    ).all()
    problems += [f"Available batch {b.code} is unscreened or empty" for b in bad_available]

    # Issued / reserved stock must reference a request (or, for issued, carry an issue movement).
    for b in db.scalars(select(InventoryBatch).where(InventoryBatch.status == InventoryStatus.RESERVED)):
        if b.allocated_request_id is None:
            problems.append(f"Reserved batch {b.code} has no request")

    # Every batch has a receipt (or transfer-in) movement and its last movement matches its status.
    last_moves = dict(db.execute(select(StockMovement.batch_id, func.max(StockMovement.id)).group_by(StockMovement.batch_id)).all())
    moves = {m.id: m for m in db.scalars(select(StockMovement).where(StockMovement.id.in_(last_moves.values())))}
    for b in db.scalars(select(InventoryBatch)):
        mid = last_moves.get(b.id)
        if mid is None:
            problems.append(f"Batch {b.code} has no stock movements")
        elif moves[mid].to_status != b.status:
            problems.append(f"Batch {b.code} status {b.status} differs from last movement {moves[mid].to_status}")

    first_types = (
        db.execute(
            select(StockMovement.movement_type).where(
                StockMovement.id.in_(select(func.min(StockMovement.id)).group_by(StockMovement.batch_id))
            )
        )
        .scalars()
        .all()
    )
    if any(t not in (MovementType.RECEIVED, MovementType.TRANSFER_IN, MovementType.TRANSFER_OUT) for t in first_types):
        problems.append("Some batches do not start with a receipt or transfer movement")

    # Requests: fulfilment counts equal issued units; histories follow the lifecycle.
    issued = dict(
        db.execute(
            select(StockMovement.request_id, func.sum(StockMovement.quantity))
            .where(StockMovement.movement_type == MovementType.ISSUED, StockMovement.request_id.is_not(None))
            .group_by(StockMovement.request_id)
        ).all()
    )
    for req in db.scalars(select(BloodRequest)):
        if req.units_fulfilled != issued.get(req.id, 0):
            problems.append(f"{req.code}: units_fulfilled {req.units_fulfilled} != issued {issued.get(req.id, 0)}")
        history = db.scalars(
            select(RequestStatusChange)
            .where(RequestStatusChange.request_id == req.id)
            .order_by(RequestStatusChange.changed_at, RequestStatusChange.id)
        ).all()
        if not history or history[-1].to_status != req.status:
            problems.append(f"{req.code}: history does not end at current status")
        for prev, nxt in zip(history, history[1:], strict=False):
            if not can_transition(prev.to_status, nxt.to_status):
                problems.append(f"{req.code}: illegal transition {prev.to_status} -> {nxt.to_status}")
            if nxt.changed_at < prev.changed_at:
                problems.append(f"{req.code}: history out of order")
        if (req.status in TERMINAL) != (req.closed_at is not None):
            problems.append(f"{req.code}: closed_at inconsistent with status {req.status}")
        if req.status.value == "fulfilled" and req.units_fulfilled != req.units_required:
            problems.append(f"{req.code}: fulfilled without all units")

    # Allocated stock is compatible with the request it was allocated to.
    rows = db.execute(
        select(
            InventoryBatch.code, InventoryBatch.blood_group, BloodRequest.blood_group, BloodRequest.component, InventoryBatch.component
        ).join(BloodRequest, BloodRequest.id == InventoryBatch.allocated_request_id)
    ).all()
    for code, donor_group, recip_group, req_comp, batch_comp in rows:
        if batch_comp != req_comp or donor_group not in compatible_donor_groups(recip_group, req_comp):
            problems.append(f"Batch {code} allocated to an incompatible request")

    # Donors: last donation date mirrors completed donations; withdrawn consent means unavailable.
    last = dict(
        db.execute(
            select(Donation.donor_id, func.max(Donation.donated_on))
            .where(Donation.status == DonationStatus.COMPLETED)
            .group_by(Donation.donor_id)
        ).all()
    )
    for donor in db.scalars(select(Donor)):
        if donor.last_donation_date != last.get(donor.id):
            problems.append(f"{donor.code}: last_donation_date inconsistent with donations")
        if donor.consent_status == ConsentStatus.WITHDRAWN and donor.availability_status.value == "available":
            problems.append(f"{donor.code}: available despite withdrawn consent")

    return problems
