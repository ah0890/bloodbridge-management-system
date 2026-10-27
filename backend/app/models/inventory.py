from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime
from app.models.enums import BloodGroup, Component, InventoryStatus, MovementType, Provenance, ScreeningStatus, str_enum
from app.models.organization import BloodBank


class InventoryBatch(TimestampMixin, Base):
    """A lot of identical units (same bank, group, component, collection/expiry) sharing one status.

    Partial reservations or issues split the batch so that every row has exactly one status.
    Usable stock = status AVAILABLE, screening PASSED and expires_on >= today.
    """

    __tablename__ = "inventory_batches"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("expires_on >= collected_on", name="expiry_after_collection"),
        Index("ix_inventory_usable", "status", "blood_group", "component", "expires_on"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    blood_bank_id: Mapped[int] = mapped_column(ForeignKey("blood_banks.id", ondelete="RESTRICT"), nullable=False, index=True)
    blood_group: Mapped[BloodGroup] = mapped_column(str_enum(BloodGroup, "blood_group"), nullable=False)
    component: Mapped[Component] = mapped_column(str_enum(Component, "component"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    collected_on: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[InventoryStatus] = mapped_column(str_enum(InventoryStatus, "inventory_status"), nullable=False)
    screening_status: Mapped[ScreeningStatus] = mapped_column(str_enum(ScreeningStatus, "screening_status"), nullable=False)
    storage_location: Mapped[str | None] = mapped_column(String(80))
    source_donation_id: Mapped[int | None] = mapped_column(ForeignKey("donations.id", ondelete="SET NULL"))
    source_reference: Mapped[str | None] = mapped_column(String(120))
    parent_batch_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_batches.id", ondelete="SET NULL"))
    allocated_request_id: Mapped[int | None] = mapped_column(ForeignKey("blood_requests.id", ondelete="SET NULL"), index=True)
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False)

    blood_bank: Mapped[BloodBank] = relationship()


class StockMovement(Base):
    """Immutable ledger of every inventory change."""

    __tablename__ = "stock_movements"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("inventory_batches.id", ondelete="RESTRICT"), nullable=False, index=True)
    blood_bank_id: Mapped[int] = mapped_column(ForeignKey("blood_banks.id", ondelete="RESTRICT"), nullable=False, index=True)
    movement_type: Mapped[MovementType] = mapped_column(str_enum(MovementType, "movement_type"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    from_status: Mapped[InventoryStatus | None] = mapped_column(str_enum(InventoryStatus, "inventory_status"))
    to_status: Mapped[InventoryStatus] = mapped_column(str_enum(InventoryStatus, "inventory_status"), nullable=False)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("blood_requests.id", ondelete="SET NULL"), index=True)
    counterpart_bank_id: Mapped[int | None] = mapped_column(ForeignKey("blood_banks.id", ondelete="RESTRICT"))
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(300))
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False)

    batch: Mapped[InventoryBatch] = relationship()
