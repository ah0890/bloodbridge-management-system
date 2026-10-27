import os
import tempfile
from pathlib import Path

# Configure an isolated database before the application is imported.
_TMP = Path(tempfile.mkdtemp(prefix="bloodbridge-test-"))
os.environ["BB_DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"
os.environ["BB_ENVIRONMENT"] = "test"
os.environ["BB_SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import CSRF_HEADER, hash_password, rate_limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import BloodBank, User  # noqa: E402
from app.models.enums import OrgType, Provenance, Role, VerificationStatus  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
TEST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    """Build the schema through Alembic so migrations themselves are exercised."""
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    rate_limiter.reset()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def make_bank(db, code="BB-T1", city="Islamabad", **kw) -> BloodBank:
    bank = BloodBank(
        code=code,
        name=kw.pop("name", f"Test Blood Bank {code}"),
        org_type=kw.pop("org_type", OrgType.BLOOD_BANK),
        city=city,
        provenance=kw.pop("provenance", Provenance.SYNTHETIC),
        verification_status=kw.pop("verification_status", VerificationStatus.VERIFIED),
        supported_components=kw.pop("supported_components", ["whole_blood", "red_cells", "plasma", "platelets"]),
        **kw,
    )
    db.add(bank)
    db.commit()
    return bank


def make_user(db, role: Role, email: str | None = None, bank: BloodBank | None = None, **kw) -> User:
    user = User(
        email=email or f"{role.value}@example.test",
        full_name=kw.pop("full_name", f"Test {role.value}"),
        password_hash=hash_password(TEST_PASSWORD),
        role=role,
        blood_bank_id=bank.id if bank else None,
        **kw,
    )
    db.add(user)
    db.commit()
    return user


def login(client: TestClient, email: str, password: str = TEST_PASSWORD) -> TestClient:
    """Sign in and attach the CSRF header so subsequent writes are accepted."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    client.headers[CSRF_HEADER] = res.json()["csrf_token"]
    return client
