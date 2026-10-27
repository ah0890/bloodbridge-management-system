from datetime import date

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models import BloodBank, BloodRequest, Donation, Donor, InventoryBatch, StockMovement, User
from app.models.enums import InventoryStatus, Provenance, Role
from app.seed import SeedError, seed_demo
from app.seed.generator import SeedConfig
from app.seed.validate import validate_dataset

from .conftest import make_bank

SMALL = dict(donors=200, banks=20, requests=40, stock_batches=60, staff_password="demo-password-for-tests")


def _cfg(**kw) -> SeedConfig:
    return SeedConfig(anchor=date(2026, 10, 27), **{**SMALL, **kw})


def _snapshot(db) -> dict:
    return {
        "donors": [
            (d.code, d.display_name, d.blood_group, d.city, d.availability_status, d.last_donation_date)
            for d in db.scalars(select(Donor).order_by(Donor.code))
        ],
        "requests": [
            (r.code, r.blood_group, r.status, r.units_fulfilled) for r in db.scalars(select(BloodRequest).order_by(BloodRequest.code))
        ],
        "batches": [
            (b.code, b.blood_group, b.component, b.quantity, b.status)
            for b in db.scalars(select(InventoryBatch).order_by(InventoryBatch.code))
        ],
    }


def test_seed_is_consistent_and_entirely_synthetic(db):
    summary = seed_demo(db, _cfg())
    assert summary.donors == 200 and summary.requests == 40
    assert validate_dataset(db) == []
    for model in (BloodBank, Donor, BloodRequest, InventoryBatch, StockMovement, Donation):
        assert db.scalar(select(func.count()).select_from(model).where(model.provenance != Provenance.SYNTHETIC)) == 0
    assert all(u.is_demo for u in db.scalars(select(User)))


def test_synthetic_contact_details_are_unreachable(db):
    seed_demo(db, _cfg())
    for d in db.scalars(select(Donor)):
        assert d.phone.startswith("+92-000-")
        assert d.email is None or d.email.endswith("@example.org")
    for b in db.scalars(select(BloodBank)):
        assert "(Demo)" in b.name and b.phone.startswith("+92-000-")
    for u in db.scalars(select(User)):
        assert u.email.endswith(".example")


def test_same_seed_and_anchor_reproduce_identical_data(db):
    seed_demo(db, _cfg())
    first = _snapshot(db)
    seed_demo(db, _cfg(), reset=True)
    assert _snapshot(db) == first


def test_different_seed_produces_different_data(db):
    seed_demo(db, _cfg())
    first = _snapshot(db)
    seed_demo(db, _cfg(seed=7), reset=True)
    assert _snapshot(db)["donors"] != first["donors"]


def test_seed_refuses_to_duplicate_without_reset(db):
    seed_demo(db, _cfg())
    with pytest.raises(SeedError, match="already exists"):
        seed_demo(db, _cfg())


def test_seed_refuses_to_mix_with_operational_data(db):
    make_bank(db, code="REAL-1", provenance=Provenance.VERIFIED)
    with pytest.raises(SeedError, match="must not be mixed"):
        seed_demo(db, _cfg())


def test_reset_preserves_non_synthetic_records(db):
    real = make_bank(db, code="REAL-1", provenance=Provenance.VERIFIED)
    seed_demo(db, _cfg(), allow_mixed=True)
    seed_demo(db, _cfg(), reset=True, allow_mixed=True)
    assert db.get(BloodBank, real.id) is not None
    assert db.scalar(select(func.count()).select_from(BloodBank).where(BloodBank.provenance == Provenance.VERIFIED)) == 1


def test_seed_refuses_in_production(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "production")
    with pytest.raises(SeedError, match="production"):
        seed_demo(db, _cfg())


def test_bank_managers_are_linked_to_stock_holding_banks(db):
    seed_demo(db, _cfg())
    managers = db.scalars(select(User).where(User.role == Role.BANK_MANAGER)).all()
    assert managers
    for m in managers:
        assert m.blood_bank is not None and m.blood_bank.supported_components


def test_validator_detects_inconsistency(db):
    seed_demo(db, _cfg())
    batch = db.scalars(select(InventoryBatch).where(InventoryBatch.status == InventoryStatus.AVAILABLE)).first()
    batch.status = InventoryStatus.ISSUED  # no matching movement
    db.flush()
    assert any(batch.code in p for p in validate_dataset(db))
    db.rollback()


def test_full_size_targets(db):
    summary = seed_demo(db, SeedConfig(anchor=date(2026, 10, 27), staff_password="demo-password-for-tests"))
    assert summary.donors == 1000
    assert 20 <= summary.blood_banks <= 50
    assert 300 <= summary.inventory_batches <= 500
    assert 100 <= summary.requests <= 200
    assert validate_dataset(db) == []
