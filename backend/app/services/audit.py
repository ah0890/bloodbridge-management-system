from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import AuditEvent, User


def record(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: object | None = None,
    summary: str,
    details: dict | None = None,
    ip: str | None = None,
    blood_bank_id: int | None = None,
) -> AuditEvent:
    """Add an audit event to the current transaction. Callers must not pass donor PII in ``details``."""
    event = AuditEvent(
        occurred_at=utcnow(),
        actor_user_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        summary=summary[:300],
        details=details,
        ip_address=ip,
        blood_bank_id=blood_bank_id if blood_bank_id is not None else (actor.blood_bank_id if actor else None),
    )
    db.add(event)
    return event
