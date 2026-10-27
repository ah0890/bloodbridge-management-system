from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import AuditEvent, BloodRequest, Donor, InventoryBatch, StockMovement
from app.models.enums import (
    AvailabilityStatus,
    BloodGroup,
    Component,
    ConsentStatus,
    ContactMethod,
    InventoryStatus,
    MovementType,
    Provenance,
    RequestPriority,
    RequestStatus,
    Role,
    ScreeningStatus,
)
from app.services.csv_export import safe_cell

from .conftest import login, make_bank, make_user

NOW = datetime.now(UTC)
TODAY = NOW.date()


def donor_payload(**kw) -> dict:
    return {
        "display_name": "Test Donor",
        "blood_group": "B+",
        "date_of_birth": (TODAY - timedelta(days=30 * 365)).isoformat(),
        "city": "Islamabad",
        "phone": "+92-000-1234567",
        "preferred_contact": "phone",
        "consent_confirmed": True,
        "availability_status": "available",
        **kw,
    }


def add_donor(db, code="DNR-T1", **kw) -> Donor:
    d = Donor(
        code=code,
        display_name=kw.pop("display_name", "Seeded Donor"),
        blood_group=kw.pop("blood_group", BloodGroup.O_POS),
        city=kw.pop("city", "Lahore"),
        phone="+92-000-7654321",
        preferred_contact=ContactMethod.PHONE,
        consent_status=kw.pop("consent_status", ConsentStatus.GRANTED),
        availability_status=kw.pop("availability_status", AvailabilityStatus.AVAILABLE),
        availability_confirmed_at=kw.pop("availability_confirmed_at", NOW - timedelta(days=3)),
        registered_at=NOW - timedelta(days=100),
        provenance=kw.pop("provenance", Provenance.SYNTHETIC),
        staff_notes="private note",
        **kw,
    )
    db.add(d)
    db.commit()
    return d


def add_batch(
    db, bank, group=BloodGroup.A_POS, qty=5, status=InventoryStatus.AVAILABLE, expires_in=10, screening=ScreeningStatus.PASSED, code="B1"
):
    b = InventoryBatch(
        code=code,
        blood_bank_id=bank.id,
        blood_group=group,
        component=Component.RED_CELLS,
        quantity=qty,
        collected_on=TODAY - timedelta(days=5),
        expires_on=TODAY + timedelta(days=expires_in),
        status=status,
        screening_status=screening,
        provenance=Provenance.SYNTHETIC,
    )
    db.add(b)
    db.flush()
    db.add(
        StockMovement(
            batch_id=b.id,
            blood_bank_id=bank.id,
            movement_type=MovementType.RECEIVED,
            quantity=qty,
            to_status=status,
            occurred_at=NOW - timedelta(days=1),
            provenance=Provenance.SYNTHETIC,
        )
    )
    db.commit()
    return b


@pytest.fixture
def coordinator(client, db):
    make_user(db, Role.COORDINATOR)
    return login(client, "coordinator@example.test")


# ---------- donors ----------
def test_create_donor_persists_with_consent_ledger_and_audit(coordinator, db):
    res = coordinator.post("/api/v1/donors", json=donor_payload())
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["code"].startswith("DNR-") and body["consent_status"] == "granted"
    assert body["currently_available"] is True
    assert body["provenance"] == "verified"  # created by a non-demo staff account
    assert len(body["consents"]) == 1 and body["phone"] == "+92-000-1234567"
    again = coordinator.get(f"/api/v1/donors/{body['id']}")
    assert again.json()["display_name"] == "Test Donor"
    events = db.scalars(select(AuditEvent).where(AuditEvent.action == "donors.create")).all()
    assert len(events) == 1 and "Test Donor" not in events[0].summary  # no names in audit summaries


def test_demo_accounts_create_synthetic_records(client, db):
    make_user(db, Role.COORDINATOR, is_demo=True)
    login(client, "coordinator@example.test")
    assert client.post("/api/v1/donors", json=donor_payload()).json()["provenance"] == "synthetic"


@pytest.mark.parametrize(
    "override,fragment",
    [
        ({"blood_group": "C+"}, "blood_group"),
        ({"consent_confirmed": False}, "consent"),
        ({"date_of_birth": (TODAY - timedelta(days=16 * 365)).isoformat()}, "ages"),
        ({"phone": "call me"}, "phone"),
        ({"phone": None}, "phone number is required"),
        ({"preferred_contact": "email", "email": None}, "email address is required"),
        ({"email": "not-an-email"}, "email"),
        ({"last_donation_date": (TODAY + timedelta(days=3)).isoformat()}, "future"),
    ],
)
def test_donor_validation(coordinator, override, fragment):
    res = coordinator.post("/api/v1/donors", json=donor_payload(**override))
    assert res.status_code == 422
    assert fragment.lower() in res.text.lower()


def test_list_search_filter_and_pagination(coordinator, db):
    for i in range(30):
        add_donor(db, code=f"DNR-{i:06d}", display_name=f"Donor {i}", blood_group=BloodGroup.A_NEG if i % 3 == 0 else BloodGroup.O_POS)
    page = coordinator.get("/api/v1/donors", params={"page_size": 10, "page": 2}).json()
    assert page["total"] == 30 and len(page["items"]) == 10 and page["page"] == 2
    assert "phone" not in page["items"][0]
    assert coordinator.get("/api/v1/donors", params={"blood_group": "A-"}).json()["total"] == 10
    assert coordinator.get("/api/v1/donors", params={"q": "dnr-000007"}).json()["total"] == 1


def test_currently_available_excludes_stale_withdrawn_and_recent_donors(coordinator, db):
    add_donor(db, code="D-OK")
    add_donor(db, code="D-STALE", availability_confirmed_at=NOW - timedelta(days=200))
    add_donor(db, code="D-NOCONSENT", consent_status=ConsentStatus.WITHDRAWN)
    add_donor(db, code="D-RECENT", last_donation_date=TODAY - timedelta(days=20))
    items = coordinator.get("/api/v1/donors", params={"currently_available": True}).json()["items"]
    assert [i["code"] for i in items] == ["D-OK"]


def test_update_availability_and_consent(coordinator, db):
    d = add_donor(db)
    res = coordinator.post(f"/api/v1/donors/{d.id}/consent", json={"status": "withdrawn", "method": "verbal_phone"})
    assert res.json()["availability_status"] == "unavailable"
    res = coordinator.post(f"/api/v1/donors/{d.id}/availability", json={"status": "available"})
    assert res.status_code == 409  # cannot mark available without consent
    res = coordinator.post(f"/api/v1/donors/{d.id}/contact-attempts", json={"method": "phone", "outcome": "no_answer"})
    assert res.status_code == 409


def test_contact_attempt_recorded_without_sending(coordinator, db):
    d = add_donor(db)
    res = coordinator.post(f"/api/v1/donors/{d.id}/contact-attempts", json={"method": "phone", "outcome": "reported_not_eligible"})
    assert res.status_code == 201
    detail = coordinator.get(f"/api/v1/donors/{d.id}").json()
    assert detail["availability_status"] == "temporarily_deferred"
    assert len(detail["contact_attempts"]) == 1


def test_bank_manager_cannot_access_donors(client, db):
    bank = make_bank(db)
    make_user(db, Role.BANK_MANAGER, bank=bank)
    login(client, "bank_manager@example.test")
    d = add_donor(db)
    assert client.get("/api/v1/donors").status_code == 403
    assert client.get(f"/api/v1/donors/{d.id}").status_code == 403
    assert client.post("/api/v1/donors", json=donor_payload()).status_code == 403


def test_admin_sees_contact_details_only_with_contact_permission(client, db):
    make_user(db, Role.ADMIN)
    login(client, "admin@example.test")
    d = add_donor(db)
    body = client.get(f"/api/v1/donors/{d.id}").json()
    assert body["phone"] and body["staff_notes"] == "private note"
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "donors.view_contact")) is not None


def test_anonymize_is_admin_only_and_irreversible(client, db, coordinator):
    d = add_donor(db)
    assert coordinator.post(f"/api/v1/donors/{d.id}/anonymize").status_code == 403
    client.cookies.clear()
    make_user(db, Role.ADMIN)
    login(client, "admin@example.test")
    body = client.post(f"/api/v1/donors/{d.id}/anonymize").json()
    assert body["phone"] is None and body["display_name"].startswith("Anonymised") and body["is_active"] is False
    assert client.post(f"/api/v1/donors/{d.id}/reactivate").status_code == 409
    assert db.get(Donor, d.id) is not None  # history preserved, not deleted


def test_export_is_minimised_labelled_and_injection_safe(coordinator, db):
    add_donor(db, display_name='=HYPERLINK("http://evil")')
    res = coordinator.get("/api/v1/donors/export.csv")
    assert res.status_code == 200
    text = res.text
    assert text.startswith("# SYNTHETIC DEMO DATA")
    assert "+92-000" not in text and "private note" not in text
    assert "'=HYPERLINK" in text
    assert "SYNTHETIC_DEMO" in res.headers["content-disposition"]


def test_safe_cell():
    assert safe_cell("=1+1") == "'=1+1" and safe_cell("@x") == "'@x" and safe_cell("Ali") == "Ali" and safe_cell(None) == ""


# ---------- dashboard ----------
def test_dashboard_requires_login(client):
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_kpis_follow_definitions(coordinator, db):
    bank = make_bank(db, city="Lahore")
    add_batch(db, bank, qty=5, code="OK")
    add_batch(db, bank, qty=3, expires_in=3, code="SOON")
    add_batch(db, bank, qty=7, status=InventoryStatus.QUARANTINED, screening=ScreeningStatus.PENDING, code="Q")
    add_batch(db, bank, qty=4, expires_in=-1, code="EXP")
    add_batch(db, bank, qty=2, status=InventoryStatus.RESERVED, code="RES")
    add_donor(db)
    add_donor(db, code="D2", availability_confirmed_at=NOW - timedelta(days=300))
    db.add(
        BloodRequest(
            code="REQ-1",
            blood_group=BloodGroup.B_POS,
            component=Component.RED_CELLS,
            units_required=2,
            city="Lahore",
            hospital_name="H (Demo)",
            required_by=NOW + timedelta(hours=5),
            priority=RequestPriority.CRITICAL,
            status=RequestStatus.SEARCHING,
            requester_name="X",
            requester_phone="+92-000-1",
            consent_at=NOW,
            submitted_via="staff",
            submitted_at=NOW,
            provenance=Provenance.SYNTHETIC,
        )
    )
    db.commit()
    k = coordinator.get("/api/v1/dashboard/summary").json()["kpis"]
    assert k["available_units"] == 8  # quarantined, expired and reserved excluded
    assert k["expiring_units"] == 3
    assert k["registered_donors"] == 2 and k["available_donors"] == 1
    assert k["active_requests"] == 1 and k["critical_or_overdue_requests"] == 1
    assert k["verified_blood_banks"] == 1
    assert coordinator.get("/api/v1/dashboard/summary", params={"city": "Karachi"}).json()["kpis"]["available_units"] == 0
    assert coordinator.get("/api/v1/dashboard/summary", params={"blood_group": "A+"}).json()["stock_by_group"]["A+"] == 8


def test_bank_manager_dashboard_is_scoped_to_own_org(client, db):
    own, other = make_bank(db, code="OWN"), make_bank(db, code="OTHER")
    add_batch(db, own, qty=4, code="A")
    add_batch(db, other, qty=9, code="B")
    make_user(db, Role.BANK_MANAGER, bank=own)
    login(client, "bank_manager@example.test")
    res = client.get("/api/v1/dashboard/summary", params={"blood_bank_id": other.id}).json()
    assert res["kpis"]["available_units"] == 4 and res["scope"]["org_scoped"] is True


def test_activity_and_city_views(coordinator, db):
    bank = make_bank(db, city="Quetta")
    add_batch(db, bank, qty=2)
    feed = coordinator.get("/api/v1/dashboard/activity").json()
    assert feed and feed[0]["kind"] == "stock_received"
    cities = coordinator.get("/api/v1/dashboard/cities").json()
    assert cities[0]["city"] == "Quetta" and cities[0]["available_units"] == 2


def test_search_respects_permissions(client, db):
    add_donor(db, code="DNR-SEARCH")
    bank = make_bank(db)
    make_user(db, Role.BANK_MANAGER, bank=bank)
    login(client, "bank_manager@example.test")
    assert client.get("/api/v1/search", params={"q": "DNR-SEARCH"}).json()["donors"] == []


def test_date_type_is_used(db):
    assert isinstance(TODAY, date)
