"""Deterministic SYNTHETIC DEMO DATA generator.

Every record created here has ``provenance = synthetic`` (or ``is_demo = True`` for staff accounts), uses reserved
or deliberately invalid contact details (``example.org`` / ``example`` domains and the non-existent ``+92-000``
prefix), and is internally consistent: inventory batches reference real banks and donations, issued/reserved
stock references the request it was allocated to, request status histories follow the lifecycle rules, and
``units_fulfilled`` equals the units actually issued.

Given the same ``seed`` and ``anchor`` date the output is identical.
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AuditEvent,
    BloodBank,
    BloodRequest,
    ContactAttempt,
    Donation,
    Donor,
    DonorAvailabilityChange,
    DonorConsent,
    InventoryBatch,
    Notification,
    RequestStatusChange,
    StockMovement,
    User,
)
from app.models.enums import (
    AvailabilityStatus,
    BloodGroup,
    Component,
    ConsentStatus,
    ContactMethod,
    ContactOutcome,
    DonationStatus,
    DonorVerification,
    InventoryStatus,
    MovementType,
    NotificationKind,
    OrgType,
    Provenance,
    RequestPriority,
    RequestStatus,
    Role,
    ScreeningStatus,
    VerificationStatus,
)
from app.seed import reference as ref
from app.services.compatibility import compatible_donor_groups
from app.services.lifecycle import check_transition

SYN = Provenance.SYNTHETIC
DEMO_EMAIL_DOMAIN = "bloodbridge-demo.example"
DEFAULT_SEED = 20261027

CITY_CODES = {
    "Karachi": "KHI",
    "Lahore": "LHE",
    "Faisalabad": "FSD",
    "Rawalpindi": "RWP",
    "Islamabad": "ISB",
    "Gujranwala": "GRW",
    "Multan": "MUX",
    "Hyderabad": "HDD",
    "Peshawar": "PEW",
    "Quetta": "UET",
    "Sialkot": "SKT",
    "Bahawalpur": "BHV",
    "Sargodha": "SGD",
    "Abbottabad": "ABT",
    "Sukkur": "SKZ",
}


def _storage_kind(component: Component) -> str:
    if component == Component.PLATELETS:
        return "Platelet agitator"
    if component in (Component.WHOLE_BLOOD, Component.RED_CELLS):
        return "Fridge"
    return "Freezer"


@dataclass
class SeedConfig:
    seed: int = DEFAULT_SEED
    anchor: date = field(default_factory=lambda: datetime.now(UTC).date())
    donors: int = 1000
    banks: int = 32
    requests: int = 160
    stock_batches: int = 330  # free stock, in addition to batches allocated to requests
    staff_password: str | None = None
    deferral_days: int = 90


@dataclass
class SeedSummary:
    blood_banks: int = 0
    users: int = 0
    donors: int = 0
    donations: int = 0
    inventory_batches: int = 0
    stock_movements: int = 0
    requests: int = 0
    contact_attempts: int = 0
    notifications: int = 0
    staff_accounts: list[tuple[str, str]] = field(default_factory=list)


class _Gen:
    def __init__(self, db: Session, cfg: SeedConfig):
        self.db = db
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        # All generated events happen strictly before the anchor instant.
        self.now = datetime.combine(cfg.anchor, time(0, 0), UTC)
        self.summary = SeedSummary()
        self.banks: list[BloodBank] = []
        self.stock_banks: list[BloodBank] = []
        self.coordinators: list[User] = []
        self.staff: list[User] = []
        self.donors: list[Donor] = []
        self.batch_seq = 0
        self.donation_seq = 0

    # ---------- helpers ----------
    def weighted(self, weights: dict):
        keys = list(weights)
        return self.rng.choices(keys, weights=[weights[k] for k in keys])[0]

    def between(self, start: datetime, end: datetime) -> datetime:
        if end <= start:
            return start
        span = (end - start).total_seconds()
        return start + timedelta(seconds=self.rng.uniform(0, span))

    def days_ago(self, lo: float, hi: float) -> datetime:
        return self.now - timedelta(days=self.rng.uniform(lo, hi))

    def phone(self) -> str:
        # +92-000 is not an allocated Pakistani prefix: the number cannot reach a real person.
        return f"+92-000-{self.rng.randint(0, 9_999_999):07d}"

    def person_name(self) -> str:
        pool = ref.GIVEN_NAMES_F if self.rng.random() < 0.3 else ref.GIVEN_NAMES_M
        return f"{self.rng.choice(pool)} {self.rng.choice(ref.FAMILY_NAMES)}"

    def city(self) -> tuple[str, float, float, int, list[str]]:
        return self.rng.choices(ref.CITIES, weights=[c[3] for c in ref.CITIES])[0]

    def blood_group(self) -> BloodGroup:
        return BloodGroup(self.weighted(ref.BLOOD_GROUP_WEIGHTS))

    def move(self, batch: InventoryBatch, mtype: MovementType, frm, to, at: datetime, qty: int | None = None, **kw):
        self.db.add(
            StockMovement(
                batch_id=batch.id,
                blood_bank_id=batch.blood_bank_id,
                movement_type=mtype,
                quantity=qty if qty is not None else batch.quantity,
                from_status=frm,
                to_status=to,
                occurred_at=at,
                provenance=SYN,
                **kw,
            )
        )
        self.summary.stock_movements += 1
        bank = self.bank_by_id[batch.blood_bank_id]
        if bank.inventory_updated_at is None or at > bank.inventory_updated_at:
            bank.inventory_updated_at = at

    # ---------- organisations and staff ----------
    def make_banks(self) -> None:
        cities = list(ref.CITIES)
        chosen = [c for c in cities] + self.rng.choices(cities, weights=[c[3] for c in cities], k=max(0, self.cfg.banks - len(cities)))
        per_city: dict[str, int] = {}
        words = list(ref.ORG_WORDS)
        for i, (city, *_rest) in enumerate(chosen):
            per_city[city] = per_city.get(city, 0) + 1
            org_type, form = ref.ORG_FORMS[0 if per_city[city] == 1 else self.rng.randrange(len(ref.ORG_FORMS))]
            word = words[i % len(words)]
            code = f"DEMO-{CITY_CODES[city]}-{per_city[city]:02d}"
            status = VerificationStatus.VERIFIED
            if per_city[city] > 1:
                status = VerificationStatus(self.weighted({"verified": 76, "pending": 16, "suspended": 8}))
            comps = [] if org_type == "hospital" else ["whole_blood", "red_cells", "plasma", "platelets"]
            if org_type != "hospital" and self.rng.random() < 0.4:
                comps.append("cryoprecipitate")
            bank = BloodBank(
                code=code,
                name=f"{word} {form}, {city} (Demo)",
                org_type=OrgType(org_type),
                city=city,
                address=f"Fictional address, {self.rng.choice(_rest[3])}, {city}",
                phone=self.phone(),
                email=f"{code.lower()}@example.org",
                operating_hours="24/7" if org_type != "hospital" and self.rng.random() < 0.5 else "08:00–20:00",
                supported_components=comps,
                verification_status=status,
                provenance=SYN,
                source_reference="Synthetic demo generator",
                last_verified_at=self.days_ago(5, 200) if status == VerificationStatus.VERIFIED else None,
                is_active=status != VerificationStatus.SUSPENDED,
            )
            self.banks.append(bank)
        self.db.add_all(self.banks)
        self.db.flush()
        self.bank_by_id = {b.id: b for b in self.banks}
        self.stock_banks = [
            b for b in self.banks if b.supported_components and b.is_active and b.verification_status == VerificationStatus.VERIFIED
        ]
        self.summary.blood_banks = len(self.banks)

    def make_staff(self) -> None:
        if not self.cfg.staff_password:
            return
        pw_hash = hash_password(self.cfg.staff_password)
        specs: list[tuple[str, str, Role, BloodBank | None]] = [(f"admin@{DEMO_EMAIL_DOMAIN}", "Demo Platform Admin", Role.ADMIN, None)]
        for i, city in enumerate(["Islamabad", "Lahore", "Karachi", "Peshawar"], start=1):
            specs.append((f"coordinator{i}@{DEMO_EMAIL_DOMAIN}", f"Demo Coordinator ({city})", Role.COORDINATOR, None))
        seen_cities: set[str] = set()
        for bank in self.stock_banks:
            if bank.city in seen_cities or len(seen_cities) >= 8:
                continue
            seen_cities.add(bank.city)
            specs.append((f"manager.{bank.code.lower()}@{DEMO_EMAIL_DOMAIN}", f"Demo Manager ({bank.city})", Role.BANK_MANAGER, bank))
        for email, name, role, bank in specs:
            user = User(
                email=email,
                full_name=name,
                password_hash=pw_hash,
                role=role,
                blood_bank_id=bank.id if bank else None,
                is_demo=True,
                created_at=self.days_ago(200, 400),
            )
            self.staff.append(user)
            if role == Role.COORDINATOR:
                self.coordinators.append(user)
            self.summary.staff_accounts.append((email, role.value))
        self.db.add_all(self.staff)
        self.db.flush()
        self.summary.users = len(self.staff)

    # ---------- donors and donations ----------
    def make_donors(self) -> None:
        cfg, rng = self.cfg, self.rng
        for i in range(cfg.donors):
            city, lat, lng, _w, localities = self.city()
            registered = self.days_ago(3, 1100)
            age = rng.randint(18, 60)
            dob = cfg.anchor - timedelta(days=age * 365 + rng.randint(0, 364))
            has_email = rng.random() < 0.45
            preferred = ContactMethod(self.weighted({"phone": 50, "whatsapp": 30, "sms": 15, "email": 5 if has_email else 0}))
            consent = ConsentStatus.GRANTED if rng.random() < 0.93 else ConsentStatus.WITHDRAWN
            donor = Donor(
                code=f"DNR-{i + 1:06d}",
                display_name=self.person_name(),
                blood_group=self.blood_group(),
                date_of_birth=dob,
                city=city,
                locality=rng.choice(localities),
                # area-level only: jitter around the city centroid, rounded to ~1 km
                latitude=round(lat + rng.uniform(-0.07, 0.07), 2),
                longitude=round(lng + rng.uniform(-0.07, 0.07), 2),
                phone=self.phone(),
                email=f"donor{i + 1:05d}@example.org" if has_email else None,
                preferred_contact=preferred,
                consent_status=ConsentStatus.GRANTED,
                consent_at=registered,
                availability_status=AvailabilityStatus.UNKNOWN,
                registered_at=registered,
                verification_status=DonorVerification(self.weighted({"unverified": 38, "phone_confirmed": 42, "screened": 20})),
                provenance=SYN,
                is_active=rng.random() < 0.97,
                created_at=registered,
            )
            self.db.add(donor)
            self.donors.append(donor)
            donor._target_consent = consent  # type: ignore[attr-defined]
        self.db.flush()

        for donor in self.donors:
            self.db.add(
                DonorConsent(
                    donor_id=donor.id,
                    status=ConsentStatus.GRANTED,
                    method=rng.choice(["paper_form", "online_form", "verbal_phone"]),
                    recorded_at=donor.registered_at,
                )
            )
            self.db.add(
                DonorAvailabilityChange(
                    donor_id=donor.id,
                    from_status=None,
                    to_status=AvailabilityStatus.UNKNOWN,
                    changed_at=donor.registered_at,
                    source="registration",
                )
            )
            self._make_donations(donor)
            self._settle_availability(donor)
        self.summary.donors = len(self.donors)

    def _make_donations(self, donor: Donor) -> None:
        rng = self.rng
        k = self.weighted({0: 35, 1: 25, 2: 18, 3: 12, 4: 7, 5: 3})
        local = [b for b in self.stock_banks if b.city == donor.city] or self.stock_banks
        cursor = self.now - timedelta(days=rng.uniform(4, 420))
        earliest = donor.registered_at - timedelta(days=720)  # donors may have donated before joining the platform
        last_completed: date | None = None
        for _ in range(k):
            if cursor < earliest:
                break
            self.donation_seq += 1
            status = DonationStatus.COMPLETED if rng.random() < 0.95 else DonationStatus.DEFERRED
            d = Donation(
                code=f"DON-{self.donation_seq:06d}",
                donor_id=donor.id,
                blood_bank_id=rng.choice(local).id,
                donated_on=cursor.date(),
                component=Component.WHOLE_BLOOD,
                units=1,
                status=status,
                provenance=SYN,
                recorded_at=cursor + timedelta(hours=2),
                notes=None if status == DonationStatus.COMPLETED else "Deferred at pre-donation screening (synthetic)",
            )
            self.db.add(d)
            self.summary.donations += 1
            if status == DonationStatus.COMPLETED:
                last_completed = max(last_completed or d.donated_on, d.donated_on)
                donor._donations = getattr(donor, "_donations", []) + [d]  # type: ignore[attr-defined]
            cursor -= timedelta(days=rng.uniform(self.cfg.deferral_days + 15, 400))
        donor.last_donation_date = last_completed

    def _settle_availability(self, donor: Donor) -> None:
        rng = self.rng
        target_consent = donor._target_consent  # type: ignore[attr-defined]
        if target_consent == ConsentStatus.WITHDRAWN:
            at = self.between(donor.registered_at, self.now - timedelta(hours=1))
            self.db.add(DonorConsent(donor_id=donor.id, status=ConsentStatus.WITHDRAWN, method="verbal_phone", recorded_at=at))
            donor.consent_status, donor.consent_at = ConsentStatus.WITHDRAWN, at
            self._set_availability(donor, AvailabilityStatus.UNAVAILABLE, at, "consent_withdrawn")
            return
        recent = donor.last_donation_date and (self.cfg.anchor - donor.last_donation_date).days < self.cfg.deferral_days
        if recent:
            at = datetime.combine(donor.last_donation_date, time(14, 0), UTC)
            self._set_availability(donor, AvailabilityStatus.TEMPORARILY_DEFERRED, at, "post_donation_interval")
            return
        status = AvailabilityStatus(self.weighted({"available": 52, "unavailable": 16, "temporarily_deferred": 6, "unknown": 26}))
        if status == AvailabilityStatus.UNKNOWN:
            return
        # Most confirmations are recent; a minority are stale and will not count as current availability.
        lo = donor.registered_at if rng.random() < 0.3 else max(donor.registered_at, self.now - timedelta(days=80))
        at = self.between(lo, self.now - timedelta(hours=2))
        self._set_availability(donor, status, at, "donor_phone_confirmation")

    def _set_availability(self, donor: Donor, status: AvailabilityStatus, at: datetime, source: str) -> None:
        self.db.add(
            DonorAvailabilityChange(
                donor_id=donor.id, from_status=donor.availability_status, to_status=status, changed_at=at, source=source
            )
        )
        donor.availability_status = status
        donor.availability_confirmed_at = at

    # ---------- inventory ----------
    def _component_for(self, bank: BloodBank) -> Component:
        weights = {c: w for c, w in ref.COMPONENT_WEIGHTS.items() if c in bank.supported_components}
        return Component(self.weighted(weights))

    def _quantity(self, component: Component) -> int:
        return {
            Component.WHOLE_BLOOD: self.rng.randint(1, 6),
            Component.RED_CELLS: self.rng.randint(1, 8),
            Component.PLASMA: self.rng.randint(2, 10),
            Component.PLATELETS: self.rng.randint(1, 4),
            Component.CRYOPRECIPITATE: self.rng.randint(2, 8),
        }[component]

    def _new_batch(self, bank: BloodBank, group: BloodGroup, component: Component, qty: int, collected: date, **kw) -> InventoryBatch:
        self.batch_seq += 1
        b = InventoryBatch(
            code=f"BAT-{self.batch_seq:06d}",
            blood_bank_id=bank.id,
            blood_group=group,
            component=component,
            quantity=qty,
            collected_on=collected,
            expires_on=collected + timedelta(days=ref.SHELF_LIFE_DAYS[component.value]),
            status=InventoryStatus.QUARANTINED,
            screening_status=ScreeningStatus.PENDING,
            storage_location=f"{_storage_kind(component)} {self.rng.randint(1, 4)}",
            provenance=SYN,
            **kw,
        )
        self.db.add(b)
        self.db.flush()
        received_at = datetime.combine(collected, time(10, 0), UTC) + timedelta(hours=self.rng.uniform(0, 8))
        b.created_at = received_at
        self.move(b, MovementType.RECEIVED, None, InventoryStatus.QUARANTINED, received_at, note="Received pending screening")
        self.summary.inventory_batches += 1
        return b

    def _release(self, b: InventoryBatch) -> datetime:
        at = datetime.combine(b.collected_on, time(10, 0), UTC) + timedelta(hours=self.rng.uniform(20, 40))
        b.screening_status = ScreeningStatus.PASSED
        b.status = InventoryStatus.AVAILABLE
        self.move(
            b, MovementType.RELEASED, InventoryStatus.QUARANTINED, InventoryStatus.AVAILABLE, at, note="Screening passed; released to stock"
        )
        return at

    def make_stock(self) -> None:
        rng, anchor = self.rng, self.cfg.anchor
        weights = [ref.CITIES[[c[0] for c in ref.CITIES].index(b.city)][3] for b in self.stock_banks]
        donation_pool = [
            d
            for donor in self.donors
            for d in getattr(donor, "_donations", [])
            if (anchor - d.donated_on).days <= ref.SHELF_LIFE_DAYS["red_cells"] + 10
        ]
        donor_by_id = {d.id: d for d in self.donors}
        made = 0
        # Batches derived from individual recorded donations (1 unit of red cells each).
        for donation in donation_pool:
            bank = self.bank_by_id[donation.blood_bank_id]
            if bank not in self.stock_banks:
                continue
            b = self._new_batch(
                bank,
                donor_by_id[donation.donor_id].blood_group,
                Component.RED_CELLS,
                1,
                donation.donated_on,
                source_donation_id=donation.id,
                source_reference=donation.code,
            )
            self._advance_free_batch(b)
            made += 1
        while made < self.cfg.stock_batches:
            bank = rng.choices(self.stock_banks, weights=weights)[0]
            component = self._component_for(bank)
            shelf = ref.SHELF_LIFE_DAYS[component.value]
            age = rng.uniform(0, min(shelf + 20, 120))
            collected = anchor - timedelta(days=int(age))
            b = self._new_batch(
                bank,
                self.blood_group(),
                component,
                self._quantity(component),
                collected,
                source_reference=f"DEMO-DRIVE-{rng.randint(100, 999)}",
            )
            self._advance_free_batch(b)
            made += 1
        self._make_transfers()

    def _advance_free_batch(self, b: InventoryBatch) -> None:
        rng, anchor = self.rng, self.cfg.anchor
        if (anchor - b.collected_on).days < 2 and rng.random() < 0.6:
            return  # still in quarantine awaiting screening
        if rng.random() < 0.03:
            at = datetime.combine(b.collected_on, time(10, 0), UTC) + timedelta(hours=30)
            b.screening_status, b.status = ScreeningStatus.FAILED, InventoryStatus.DISCARDED
            self.move(
                b, MovementType.DISCARDED, InventoryStatus.QUARANTINED, InventoryStatus.DISCARDED, at, note="Failed screening; discarded"
            )
            return
        released_at = self._release(b)
        expiry_at = datetime.combine(b.expires_on, time(23, 59), UTC)
        if rng.random() < 0.18:
            issued_at = self.between(released_at, min(expiry_at, self.now - timedelta(hours=1)))
            if issued_at > released_at:
                b.status = InventoryStatus.ISSUED
                self.move(
                    b,
                    MovementType.ISSUED,
                    InventoryStatus.AVAILABLE,
                    InventoryStatus.ISSUED,
                    issued_at,
                    note="Issued against hospital requisition (no platform request)",
                )
                return
        if b.expires_on < anchor:
            at = expiry_at + timedelta(minutes=1)
            if rng.random() < 0.6:
                b.status = InventoryStatus.EXPIRED
                self.move(b, MovementType.EXPIRED, InventoryStatus.AVAILABLE, InventoryStatus.EXPIRED, at, note="Passed expiry date")
            else:
                b.status = InventoryStatus.DISCARDED
                self.move(b, MovementType.DISCARDED, InventoryStatus.AVAILABLE, InventoryStatus.DISCARDED, at, note="Expired; disposed")

    def _make_transfers(self) -> None:
        rng = self.rng
        pool = (
            self.db.query(InventoryBatch)
            .filter(InventoryBatch.status == InventoryStatus.AVAILABLE, InventoryBatch.quantity >= 2)
            .order_by(InventoryBatch.id)
            .all()
        )
        for b in rng.sample(pool, k=min(8, len(pool))):
            others = [x for x in self.stock_banks if x.id != b.blood_bank_id and x.city != self.bank_by_id[b.blood_bank_id].city]
            if not others:
                continue
            dest = rng.choice(others)
            qty = rng.randint(1, b.quantity - 1)
            at = self.days_ago(0.5, max(1.0, min(10, (self.cfg.anchor - b.collected_on).days - 1)))
            if at <= datetime.combine(b.collected_on, time(12, 0), UTC) + timedelta(days=2):
                continue
            b.quantity -= qty
            out = InventoryBatch(
                code=f"{b.code}-T",
                blood_bank_id=b.blood_bank_id,
                blood_group=b.blood_group,
                component=b.component,
                quantity=qty,
                collected_on=b.collected_on,
                expires_on=b.expires_on,
                status=InventoryStatus.TRANSFERRED,
                screening_status=ScreeningStatus.PASSED,
                parent_batch_id=b.id,
                source_reference=b.source_reference,
                provenance=SYN,
                storage_location=b.storage_location,
            )
            self.db.add(out)
            self.db.flush()
            self.move(
                out,
                MovementType.TRANSFER_OUT,
                InventoryStatus.AVAILABLE,
                InventoryStatus.TRANSFERRED,
                at,
                counterpart_bank_id=dest.id,
                note=f"Transferred to {dest.code}",
            )
            self.batch_seq += 1
            incoming = InventoryBatch(
                code=f"BAT-{self.batch_seq:06d}",
                blood_bank_id=dest.id,
                blood_group=b.blood_group,
                component=b.component,
                quantity=qty,
                collected_on=b.collected_on,
                expires_on=b.expires_on,
                status=InventoryStatus.AVAILABLE,
                screening_status=ScreeningStatus.PASSED,
                parent_batch_id=out.id,
                source_reference=f"Transfer from {b.code}",
                provenance=SYN,
                storage_location="Fridge 1",
            )
            self.db.add(incoming)
            self.db.flush()
            self.move(
                incoming,
                MovementType.TRANSFER_IN,
                None,
                InventoryStatus.AVAILABLE,
                at + timedelta(hours=3),
                counterpart_bank_id=b.blood_bank_id,
                note=f"Received by transfer from {self.bank_by_id[b.blood_bank_id].code}",
            )
            self.summary.inventory_batches += 2

    # ---------- requests ----------
    _OPEN_PATHS = {
        RequestStatus.SUBMITTED: [],
        RequestStatus.UNDER_REVIEW: [RequestStatus.UNDER_REVIEW],
        RequestStatus.SEARCHING: [RequestStatus.UNDER_REVIEW, RequestStatus.SEARCHING],
        RequestStatus.MATCHES_FOUND: [RequestStatus.UNDER_REVIEW, RequestStatus.SEARCHING, RequestStatus.MATCHES_FOUND],
        RequestStatus.COORDINATION: [
            RequestStatus.UNDER_REVIEW,
            RequestStatus.SEARCHING,
            RequestStatus.MATCHES_FOUND,
            RequestStatus.COORDINATION,
        ],
        RequestStatus.PARTIALLY_FULFILLED: [
            RequestStatus.UNDER_REVIEW,
            RequestStatus.SEARCHING,
            RequestStatus.MATCHES_FOUND,
            RequestStatus.COORDINATION,
            RequestStatus.PARTIALLY_FULFILLED,
        ],
    }

    def make_requests(self) -> None:
        rng = self.rng
        seq_by_year: dict[int, int] = {}
        hospitals = [b for b in self.banks if b.org_type in (OrgType.HOSPITAL, OrgType.HOSPITAL_BLOOD_BANK)]
        specs = []
        for _ in range(self.cfg.requests):
            recent = rng.random() < 0.22
            submitted = self.days_ago(0.05, 9) if recent else self.days_ago(10, 180)
            specs.append((submitted, recent))
        specs.sort(key=lambda s: s[0])
        for submitted, recent in specs:
            city = self.city()[0]
            local_stock = [b for b in self.stock_banks if b.city == city]
            local_hosp = [h for h in hospitals if h.city == city]
            component = Component(self.weighted({"red_cells": 55, "whole_blood": 23, "platelets": 13, "plasma": 9}))
            priority = RequestPriority(self.weighted({"routine": 45, "urgent": 38, "critical": 17}))
            lead = {RequestPriority.CRITICAL: (4, 12), RequestPriority.URGENT: (12, 48), RequestPriority.ROUTINE: (48, 168)}[priority]
            year = submitted.year
            seq_by_year[year] = seq_by_year.get(year, 0) + 1
            hosp_name = (
                rng.choice(local_hosp).name
                if local_hosp and rng.random() < 0.5
                else f"{rng.choice(ref.ORG_WORDS)} {rng.choice(ref.HOSPITAL_SUFFIXES)}, {city} (Demo)"
            )
            req = BloodRequest(
                code=f"REQ-{year}-{seq_by_year[year]:05d}",
                blood_group=self.blood_group(),
                component=component,
                units_required=rng.randint(1, 2) if component == Component.PLATELETS else rng.choice([1, 1, 2, 2, 2, 3, 4]),
                units_fulfilled=0,
                city=city,
                hospital_name=hosp_name,
                blood_bank_id=rng.choice(local_stock).id if local_stock else None,
                required_by=submitted + timedelta(hours=rng.uniform(*lead)),
                priority=priority,
                status=RequestStatus.SUBMITTED,
                requester_name=self.person_name(),
                requester_phone=self.phone(),
                requester_relationship=rng.choice(ref.RELATIONSHIPS),
                consent_at=submitted,
                submitted_via="public" if rng.random() < 0.65 else "staff",
                submitted_at=submitted,
                provenance=SYN,
                created_at=submitted,
            )
            self.db.add(req)
            self.db.flush()
            self.summary.requests += 1
            self.db.add(
                RequestStatusChange(
                    request_id=req.id, from_status=None, to_status=RequestStatus.SUBMITTED, changed_at=submitted, note="Request submitted"
                )
            )
            if recent:
                target = RequestStatus(
                    self.weighted(
                        {
                            "submitted": 14,
                            "under_review": 14,
                            "searching": 18,
                            "matches_found": 18,
                            "coordination_in_progress": 22,
                            "partially_fulfilled": 14,
                        }
                    )
                )
            else:
                target = RequestStatus(
                    self.weighted({"fulfilled": 64, "closed_unfulfilled": 16, "cancelled": 14, "partially_fulfilled": 0})
                )
            self._drive_request(req, target, local_stock)

    def _step(self, req: BloodRequest, to: RequestStatus, at: datetime, note: str, by: User | None = None) -> None:
        check_transition(req.status, to, units_fulfilled=req.units_fulfilled, units_required=req.units_required)
        self.db.add(
            RequestStatusChange(
                request_id=req.id, from_status=req.status, to_status=to, changed_at=at, changed_by_id=by.id if by else None, note=note
            )
        )
        req.status = to
        req.updated_at = at

    def _drive_request(self, req: BloodRequest, target: RequestStatus, local_stock: list[BloodBank]) -> None:
        rng = self.rng
        coordinator = rng.choice(self.coordinators) if self.coordinators else None
        terminal_deadline = min(self.now - timedelta(minutes=5), req.submitted_at + timedelta(days=rng.uniform(0.3, 6)))
        horizon = (
            terminal_deadline
            if target in (RequestStatus.FULFILLED, RequestStatus.CANCELLED, RequestStatus.CLOSED_UNFULFILLED)
            else self.now - timedelta(minutes=5)
        )
        t = req.submitted_at

        def tick() -> datetime:
            nonlocal t
            t = self.between(t, t + (horizon - t) / 3)
            return t

        if target == RequestStatus.CANCELLED:
            path = rng.choice([[], [RequestStatus.UNDER_REVIEW], [RequestStatus.UNDER_REVIEW, RequestStatus.SEARCHING]])
            for s in path:
                self._step(req, s, tick(), self._note(s), coordinator)
            self._step(req, RequestStatus.CANCELLED, tick(), "Cancelled by requester (patient no longer requires transfusion)")
            req.closed_at = t
            return

        path = self._OPEN_PATHS.get(target)
        if path is None:  # fulfilled / closed_unfulfilled
            via_donors = rng.random() < 0.45
            path = [RequestStatus.UNDER_REVIEW, RequestStatus.SEARCHING] + (
                [RequestStatus.MATCHES_FOUND, RequestStatus.COORDINATION] if via_donors else []
            )
        if path and coordinator:
            req.assigned_coordinator_id = coordinator.id
        for s in path:
            if s == RequestStatus.PARTIALLY_FULFILLED:
                continue
            self._step(req, s, tick(), self._note(s), coordinator)
            if s == RequestStatus.MATCHES_FOUND:
                self._contact_donors(req, t, horizon, coordinator)

        if target == RequestStatus.COORDINATION:
            if local_stock and rng.random() < 0.6:
                self._allocate(req, local_stock, rng.randint(1, req.units_required), issue=False, at=tick())
        elif target == RequestStatus.PARTIALLY_FULFILLED:
            # A single-unit request cannot be partially fulfilled; it simply remains in coordination.
            if req.units_required > 1 and local_stock:
                self._allocate(req, local_stock, rng.randint(1, req.units_required - 1), issue=True, at=tick())
                self._step(req, RequestStatus.PARTIALLY_FULFILLED, t, "Units issued; remaining units still being sourced", coordinator)
        elif target in self._OPEN_PATHS:
            pass  # other open statuses: nothing further has happened yet
        elif target == RequestStatus.FULFILLED and local_stock:
            self._allocate(req, local_stock, req.units_required, issue=True, at=tick())
            self._step(req, RequestStatus.FULFILLED, t, "All requested units issued to the hospital", coordinator)
            req.closed_at = t
            req.fulfillment_notes = f"{req.units_required} unit(s) issued from inventory."
        else:  # closed unfulfilled (or fulfilled impossible because no stock-holding bank in the city)
            if local_stock and req.units_required > 1 and rng.random() < 0.3:
                self._allocate(req, local_stock, 1, issue=True, at=tick())
            self._step(
                req, RequestStatus.CLOSED_UNFULFILLED, tick(), "Closed: required-by time passed without sourcing all units", coordinator
            )
            req.closed_at = t

    @staticmethod
    def _note(s: RequestStatus) -> str:
        return {
            RequestStatus.UNDER_REVIEW: "Details reviewed by coordinator",
            RequestStatus.SEARCHING: "Searching inventory and donor registry",
            RequestStatus.MATCHES_FOUND: "Potential donors identified for contact",
            RequestStatus.COORDINATION: "Coordinating with donors and blood bank",
        }.get(s, s.value)

    def _contact_donors(self, req: BloodRequest, start: datetime, end: datetime, coordinator: User | None) -> None:
        rng = self.rng
        groups = set(compatible_donor_groups(req.blood_group, req.component))
        pool = [
            d
            for d in self.donors
            if d.city == req.city
            and d.blood_group in groups
            and d.is_active
            and d.consent_status == ConsentStatus.GRANTED
            and d.registered_at < start
        ]
        for donor in rng.sample(pool, k=min(len(pool), rng.randint(2, 6))):
            outcome = ContactOutcome(
                self.weighted(
                    {
                        "no_answer": 30,
                        "declined": 15,
                        "agreed_to_donate": 30,
                        "reported_not_eligible": 10,
                        "callback_requested": 10,
                        "wrong_number": 5,
                    }
                )
            )
            self.db.add(
                ContactAttempt(
                    donor_id=donor.id,
                    request_id=req.id,
                    coordinator_id=coordinator.id if coordinator else None,
                    attempted_at=self.between(start, start + (end - start) / 2),
                    method=donor.preferred_contact if donor.preferred_contact != ContactMethod.EMAIL else ContactMethod.PHONE,
                    outcome=outcome,
                    provenance=SYN,
                    notes="Synthetic contact record — no message was sent",
                )
            )
            self.summary.contact_attempts += 1

    def _allocate(self, req: BloodRequest, local_stock: list[BloodBank], units: int, issue: bool, at: datetime) -> None:
        """Create batch(es) at a local bank that were reserved (and optionally issued) for ``req``."""
        rng = self.rng
        bank = self.bank_by_id[req.blood_bank_id] if req.blood_bank_id else rng.choice(local_stock)
        if req.component.value not in bank.supported_components:
            bank = next((b for b in local_stock if req.component.value in b.supported_components), bank)
        groups = compatible_donor_groups(req.blood_group, req.component)
        group = req.blood_group if req.blood_group in groups and rng.random() < 0.8 else rng.choice(groups)
        shelf = ref.SHELF_LIFE_DAYS[req.component.value]
        collected = (at - timedelta(days=rng.uniform(2.5, max(3.0, shelf * 0.6)))).date()
        b = self._new_batch(bank, group, req.component, units, collected, source_reference=f"DEMO-DRIVE-{rng.randint(100, 999)}")
        released = self._release(b)
        reserve_at = max(at, released + timedelta(hours=1))
        b.status, b.allocated_request_id = InventoryStatus.RESERVED, req.id
        self.move(
            b,
            MovementType.RESERVED,
            InventoryStatus.AVAILABLE,
            InventoryStatus.RESERVED,
            reserve_at,
            request_id=req.id,
            note=f"Reserved for {req.code}",
        )
        if issue:
            b.status = InventoryStatus.ISSUED
            self.move(
                b,
                MovementType.ISSUED,
                InventoryStatus.RESERVED,
                InventoryStatus.ISSUED,
                reserve_at + timedelta(minutes=40),
                request_id=req.id,
                note=f"Issued for {req.code}",
            )
            req.units_fulfilled += units

    # ---------- notifications and audit ----------
    def make_notifications(self) -> None:
        rng = self.rng
        critical = (
            self.db.query(BloodRequest)
            .filter(BloodRequest.priority == RequestPriority.CRITICAL)
            .order_by(BloodRequest.submitted_at.desc())
            .limit(6)
            .all()
        )
        for user in self.staff:
            for req in critical:
                if user.role == Role.BANK_MANAGER and req.blood_bank_id != user.blood_bank_id:
                    continue
                self.db.add(
                    Notification(
                        user_id=user.id,
                        kind=NotificationKind.CRITICAL_REQUEST,
                        title=(
                            f"Critical request {req.code}: {req.units_required} × "
                            f"{req.blood_group.value} {req.component.value.replace('_', ' ')}"
                        ),
                        body=f"{req.city} · required by {req.required_by:%d %b %H:%M} UTC",
                        link=f"/requests/{req.id}",
                        created_at=req.submitted_at,
                        read_at=req.submitted_at + timedelta(hours=2) if rng.random() < 0.5 else None,
                    )
                )
                self.summary.notifications += 1

    def run(self) -> SeedSummary:
        self.make_banks()
        self.make_staff()
        self.make_donors()
        self.db.flush()
        self.make_requests()
        self.make_stock()
        self.make_notifications()
        self.db.add(
            AuditEvent(
                occurred_at=self.now,
                action="seed.generated",
                entity_type="dataset",
                summary="Synthetic demo dataset generated",
                details={
                    "seed": self.cfg.seed,
                    "anchor": self.cfg.anchor.isoformat(),
                    "donors": self.summary.donors,
                    "requests": self.summary.requests,
                    "batches": self.summary.inventory_batches,
                },
            )
        )
        self.db.flush()
        return self.summary


def generate(db: Session, cfg: SeedConfig) -> SeedSummary:
    return _Gen(db, cfg).run()
