from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime
from app.models.enums import (
    AvailabilityStatus,
    BloodGroup,
    Component,
    ConsentStatus,
    ContactMethod,
    ContactOutcome,
    DonationStatus,
    DonorVerification,
    Provenance,
    str_enum,
)


class Donor(TimestampMixin, Base):
    """A potential donor. Registration is not medical eligibility; screening happens at the blood bank."""

    __tablename__ = "donors"
    __table_args__ = (
        Index("ix_donors_match", "blood_group", "city", "availability_status"),
        CheckConstraint("latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="lat_range"),
        CheckConstraint("longitude IS NULL OR (longitude BETWEEN -180 AND 180)", name="lng_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    blood_group: Mapped[BloodGroup] = mapped_column(str_enum(BloodGroup, "blood_group"), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    locality: Mapped[str | None] = mapped_column(String(120))
    # Approximate (area-level) coordinates only; never a home address.
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(200))
    preferred_contact: Mapped[ContactMethod] = mapped_column(str_enum(ContactMethod, "contact_method"), nullable=False)
    consent_status: Mapped[ConsentStatus] = mapped_column(str_enum(ConsentStatus, "consent_status"), nullable=False)
    consent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        str_enum(AvailabilityStatus, "availability_status"), default=AvailabilityStatus.UNKNOWN, nullable=False
    )
    availability_confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_donation_date: Mapped[date | None] = mapped_column(Date)
    registered_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    verification_status: Mapped[DonorVerification] = mapped_column(
        str_enum(DonorVerification, "donor_verification"), default=DonorVerification.UNVERIFIED, nullable=False
    )
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False, index=True)
    staff_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    anonymized_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    consents: Mapped[list["DonorConsent"]] = relationship(back_populates="donor", order_by="DonorConsent.recorded_at")
    availability_history: Mapped[list["DonorAvailabilityChange"]] = relationship(
        back_populates="donor", order_by="DonorAvailabilityChange.changed_at"
    )
    donations: Mapped[list["Donation"]] = relationship(back_populates="donor", order_by="Donation.donated_on")


class DonorConsent(Base):
    """Append-only consent ledger. ``Donor.consent_status`` mirrors the latest entry."""

    __tablename__ = "donor_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ConsentStatus] = mapped_column(str_enum(ConsentStatus, "consent_status"), nullable=False)
    scope: Mapped[str] = mapped_column(String(120), nullable=False, default="contact_for_blood_requests")
    method: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. paper_form, verbal_phone, online_form
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    donor: Mapped[Donor] = relationship(back_populates="consents")


class DonorAvailabilityChange(Base):
    __tablename__ = "donor_availability_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[AvailabilityStatus | None] = mapped_column(str_enum(AvailabilityStatus, "availability_status"))
    to_status: Mapped[AvailabilityStatus] = mapped_column(str_enum(AvailabilityStatus, "availability_status"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. donor_phone_confirmation, contact_attempt
    note: Mapped[str | None] = mapped_column(String(300))

    donor: Mapped[Donor] = relationship(back_populates="availability_history")


class Donation(Base):
    """A donation event recorded by an authorised user at a blood bank."""

    __tablename__ = "donations"
    __table_args__ = (CheckConstraint("units >= 1 AND units <= 4", name="units_range"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="RESTRICT"), nullable=False, index=True)
    blood_bank_id: Mapped[int] = mapped_column(ForeignKey("blood_banks.id", ondelete="RESTRICT"), nullable=False, index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("blood_requests.id", ondelete="SET NULL"), index=True)
    donated_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    component: Mapped[Component] = mapped_column(str_enum(Component, "component"), nullable=False)
    units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[DonationStatus] = mapped_column(str_enum(DonationStatus, "donation_status"), nullable=False)
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))

    donor: Mapped[Donor] = relationship(back_populates="donations")


class ContactAttempt(Base):
    """A coordinator's record of contacting a donor. Recording an attempt never sends a message."""

    __tablename__ = "contact_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("blood_requests.id", ondelete="CASCADE"), index=True)
    coordinator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    method: Mapped[ContactMethod] = mapped_column(str_enum(ContactMethod, "contact_method"), nullable=False)
    outcome: Mapped[ContactOutcome] = mapped_column(str_enum(ContactOutcome, "contact_outcome"), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False)

    donor: Mapped[Donor] = relationship()
