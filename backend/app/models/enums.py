"""Domain enumerations. Stored as constrained strings so they are portable across databases."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def str_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Role(StrEnum):
    ADMIN = "admin"
    BANK_MANAGER = "bank_manager"
    COORDINATOR = "coordinator"


class Provenance(StrEnum):
    """Where a record came from. Synthetic records must never be presented as real."""

    SYNTHETIC = "synthetic"
    IMPORTED = "imported"
    VERIFIED = "verified"


class OrgType(StrEnum):
    BLOOD_BANK = "blood_bank"
    HOSPITAL = "hospital"
    HOSPITAL_BLOOD_BANK = "hospital_blood_bank"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class BloodGroup(StrEnum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


class Component(StrEnum):
    WHOLE_BLOOD = "whole_blood"
    RED_CELLS = "red_cells"
    PLASMA = "plasma"
    PLATELETS = "platelets"
    CRYOPRECIPITATE = "cryoprecipitate"


class InventoryStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    ISSUED = "issued"
    QUARANTINED = "quarantined"
    EXPIRED = "expired"
    DISCARDED = "discarded"
    TRANSFERRED = "transferred"


class ScreeningStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class MovementType(StrEnum):
    RECEIVED = "received"
    RESERVED = "reserved"
    RESERVATION_RELEASED = "reservation_released"
    ISSUED = "issued"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    QUARANTINED = "quarantined"
    RELEASED = "released"
    EXPIRED = "expired"
    DISCARDED = "discarded"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TEMPORARILY_DEFERRED = "temporarily_deferred"
    UNKNOWN = "unknown"


class DonorVerification(StrEnum):
    UNVERIFIED = "unverified"
    PHONE_CONFIRMED = "phone_confirmed"
    SCREENED = "screened"


class ContactMethod(StrEnum):
    PHONE = "phone"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class ConsentStatus(StrEnum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


class RequestPriority(StrEnum):
    """Operational (staff-assigned) priority. This is not a medical triage level."""

    ROUTINE = "routine"
    URGENT = "urgent"
    CRITICAL = "critical"


class RequestStatus(StrEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SEARCHING = "searching"
    MATCHES_FOUND = "matches_found"
    COORDINATION = "coordination_in_progress"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    CLOSED_UNFULFILLED = "closed_unfulfilled"


class ContactOutcome(StrEnum):
    NO_ANSWER = "no_answer"
    DECLINED = "declined"
    AGREED = "agreed_to_donate"
    NOT_ELIGIBLE = "reported_not_eligible"
    WRONG_NUMBER = "wrong_number"
    CALLBACK = "callback_requested"


class DonationStatus(StrEnum):
    COMPLETED = "completed"
    DEFERRED = "deferred_at_screening"


class NotificationKind(StrEnum):
    NEW_REQUEST = "new_request"
    CRITICAL_REQUEST = "critical_request"
    REQUEST_UPDATE = "request_update"
    LOW_STOCK = "low_stock"
    EXPIRY = "expiry"
    INVENTORY = "inventory"
    ASSIGNMENT = "assignment"
    VERIFICATION = "verification"
