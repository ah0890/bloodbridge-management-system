from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime
from app.models.enums import BloodGroup, Component, Provenance, RequestPriority, RequestStatus, str_enum
from app.models.organization import BloodBank, User


class BloodRequest(TimestampMixin, Base):
    """A request for blood. Stores the minimum needed for coordination; no patient identifiers."""

    __tablename__ = "blood_requests"
    __table_args__ = (
        CheckConstraint("units_required BETWEEN 1 AND 20", name="units_required_range"),
        CheckConstraint("units_fulfilled >= 0 AND units_fulfilled <= units_required", name="units_fulfilled_range"),
        Index("ix_requests_status_priority", "status", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    blood_group: Mapped[BloodGroup] = mapped_column(str_enum(BloodGroup, "blood_group"), nullable=False, index=True)
    component: Mapped[Component] = mapped_column(str_enum(Component, "component"), nullable=False)
    units_required: Mapped[int] = mapped_column(Integer, nullable=False)
    units_fulfilled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    hospital_name: Mapped[str] = mapped_column(String(200), nullable=False)
    blood_bank_id: Mapped[int | None] = mapped_column(ForeignKey("blood_banks.id", ondelete="SET NULL"), index=True)
    required_by: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    priority: Mapped[RequestPriority] = mapped_column(str_enum(RequestPriority, "request_priority"), nullable=False)
    status: Mapped[RequestStatus] = mapped_column(str_enum(RequestStatus, "request_status"), nullable=False, index=True)
    requester_name: Mapped[str] = mapped_column(String(120), nullable=False)
    requester_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    requester_relationship: Mapped[str | None] = mapped_column(String(60))
    consent_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    submitted_via: Mapped[str] = mapped_column(String(20), nullable=False)  # public | staff | import
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    assigned_coordinator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    fulfillment_notes: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False, index=True)

    blood_bank: Mapped[BloodBank | None] = relationship()
    assigned_coordinator: Mapped[User | None] = relationship()
    history: Mapped[list["RequestStatusChange"]] = relationship(back_populates="request", order_by="RequestStatusChange.changed_at")


class RequestStatusChange(Base):
    __tablename__ = "request_status_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("blood_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[RequestStatus | None] = mapped_column(str_enum(RequestStatus, "request_status"))
    to_status: Mapped[RequestStatus] = mapped_column(str_enum(RequestStatus, "request_status"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(500))

    request: Mapped[BloodRequest] = relationship(back_populates="history")
    changed_by: Mapped[User | None] = relationship()


class MatchRun(Base):
    """One execution of the matching engine for a request, with the rules and parameters used."""

    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("blood_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    run_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    run_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rules_version: Mapped[str] = mapped_column(String(40), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    candidates_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)
    candidates_eligible: Mapped[int] = mapped_column(Integer, nullable=False)
    candidates_review: Mapped[int] = mapped_column(Integer, nullable=False)

    results: Mapped[list["MatchResult"]] = relationship(back_populates="run", order_by="MatchResult.rank")


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (Index("ix_match_results_run_donor", "match_run_id", "donor_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_run_id: Mapped[int] = mapped_column(ForeignKey("match_runs.id", ondelete="CASCADE"), nullable=False)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    factors: Mapped[list] = mapped_column(JSON, nullable=False)

    run: Mapped[MatchRun] = relationship(back_populates="results")
