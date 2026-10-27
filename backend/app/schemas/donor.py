import re
from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

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
)

PHONE_RE = re.compile(r"^\+?[0-9][0-9\- ]{6,18}[0-9]$")
MIN_AGE, MAX_AGE = 18, 65  # registration bounds only; donor eligibility is assessed at screening


def _age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def validate_phone(v: str | None) -> str | None:
    if v is None or v.strip() == "":
        return None
    v = v.strip()
    if not PHONE_RE.match(v):
        raise ValueError("Enter a valid phone number (digits, spaces or dashes, optional leading +).")
    return v


def validate_dob(v: date | None) -> date | None:
    if v is not None:
        age = _age_on(v, datetime.now(UTC).date())
        if not MIN_AGE <= age <= MAX_AGE:
            raise ValueError(f"Registration is limited to ages {MIN_AGE}–{MAX_AGE}.")
    return v


class DonorBase(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    blood_group: BloodGroup
    date_of_birth: date | None = None
    city: str = Field(min_length=2, max_length=80)
    locality: str | None = Field(None, max_length=120)
    phone: str | None = Field(None, max_length=40)
    email: EmailStr | None = None
    preferred_contact: ContactMethod = ContactMethod.PHONE
    verification_status: DonorVerification = DonorVerification.UNVERIFIED
    staff_notes: str | None = Field(None, max_length=2000)

    @field_validator("display_name", "city", "locality", "staff_notes")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    _phone = field_validator("phone")(lambda cls, v: validate_phone(v))
    _dob = field_validator("date_of_birth")(lambda cls, v: validate_dob(v))

    @model_validator(mode="after")
    def _contact_present(self):
        if self.preferred_contact == ContactMethod.EMAIL and not self.email:
            raise ValueError("An email address is required when email is the preferred contact method.")
        if self.preferred_contact != ContactMethod.EMAIL and not self.phone:
            raise ValueError("A phone number is required for phone, SMS or WhatsApp contact.")
        return self


class DonorCreate(DonorBase):
    consent_confirmed: bool = Field(description="Donor has consented to be contacted for blood requests")
    consent_method: str = Field("paper_form", pattern=r"^(paper_form|online_form|verbal_phone|in_person)$")
    availability_status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    last_donation_date: date | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    @field_validator("consent_confirmed")
    @classmethod
    def _consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Donor consent is required before registration.")
        return v

    @field_validator("last_donation_date")
    @classmethod
    def _past(cls, v: date | None) -> date | None:
        if v and v > datetime.now(UTC).date():
            raise ValueError("Last donation date cannot be in the future.")
        return v


class DonorUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=120)
    blood_group: BloodGroup | None = None
    date_of_birth: date | None = None
    city: str | None = Field(None, min_length=2, max_length=80)
    locality: str | None = Field(None, max_length=120)
    phone: str | None = Field(None, max_length=40)
    email: EmailStr | None = None
    preferred_contact: ContactMethod | None = None
    verification_status: DonorVerification | None = None
    staff_notes: str | None = Field(None, max_length=2000)

    _phone = field_validator("phone")(lambda cls, v: validate_phone(v))
    _dob = field_validator("date_of_birth")(lambda cls, v: validate_dob(v))


class AvailabilityUpdate(BaseModel):
    status: AvailabilityStatus
    source: str = Field("donor_phone_confirmation", pattern=r"^(donor_phone_confirmation|donor_in_person|contact_attempt|staff_review)$")
    note: str | None = Field(None, max_length=300)


class ConsentUpdate(BaseModel):
    status: ConsentStatus
    method: str = Field(pattern=r"^(paper_form|online_form|verbal_phone|in_person)$")


class ContactAttemptCreate(BaseModel):
    request_id: int | None = None
    method: ContactMethod
    outcome: ContactOutcome
    notes: str | None = Field(None, max_length=500)


class DonorListItem(BaseModel):
    """List view: no contact details."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    display_name: str
    blood_group: BloodGroup
    city: str
    locality: str | None
    availability_status: AvailabilityStatus
    availability_confirmed_at: datetime | None
    consent_status: ConsentStatus
    verification_status: DonorVerification
    last_donation_date: date | None
    registered_at: datetime
    provenance: Provenance
    is_active: bool
    currently_available: bool = False


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: ConsentStatus
    scope: str
    method: str
    recorded_at: datetime


class AvailabilityChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    from_status: AvailabilityStatus | None
    to_status: AvailabilityStatus
    changed_at: datetime
    source: str
    note: str | None


class DonationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    donor_id: int
    blood_bank_id: int
    request_id: int | None
    donated_on: date
    component: Component
    units: int
    status: DonationStatus
    provenance: Provenance
    notes: str | None


class ContactAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    donor_id: int
    request_id: int | None
    attempted_at: datetime
    method: ContactMethod
    outcome: ContactOutcome
    notes: str | None
    provenance: Provenance


class DonorDetail(DonorListItem):
    date_of_birth: date | None
    age: int | None = None
    latitude: float | None
    longitude: float | None
    preferred_contact: ContactMethod
    consent_at: datetime | None
    anonymized_at: datetime | None
    # Present only for users permitted to see contact details; otherwise null.
    phone: str | None = None
    email: str | None = None
    staff_notes: str | None = None
    consents: list[ConsentOut] = []
    availability_history: list[AvailabilityChangeOut] = []
    donations: list[DonationOut] = []
    contact_attempts: list[ContactAttemptOut] = []
