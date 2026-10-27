from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime
from app.models.enums import OrgType, Provenance, Role, VerificationStatus, str_enum


class BloodBank(TimestampMixin, Base):
    """A participating organization (blood bank or hospital)."""

    __tablename__ = "blood_banks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[OrgType] = mapped_column(str_enum(OrgType, "org_type"), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    operating_hours: Mapped[str | None] = mapped_column(String(120))
    supported_components: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        str_enum(VerificationStatus, "verification_status"), default=VerificationStatus.PENDING, nullable=False
    )
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(300))
    last_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    inventory_updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="blood_bank")


class User(TimestampMixin, Base):
    """A staff account. Public users are unauthenticated and have no row here."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"), nullable=False)
    blood_bank_id: Mapped[int | None] = mapped_column(ForeignKey("blood_banks.id", ondelete="RESTRICT"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    blood_bank: Mapped[BloodBank | None] = relationship(back_populates="users")


class AuditEvent(Base):
    """Append-only record of security-relevant and operational actions. Never stores donor PII."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(String(300), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    blood_bank_id: Mapped[int | None] = mapped_column(ForeignKey("blood_banks.id", ondelete="SET NULL"), index=True)

    actor: Mapped[User | None] = relationship()

