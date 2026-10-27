from app.core.security import CSRF_HEADER, SESSION_COOKIE, hash_password, verify_password
from app.models import AuditEvent
from app.models.enums import Role

from .conftest import TEST_PASSWORD, login, make_bank, make_user


def test_password_hashing_is_salted_and_verifiable():
    h1, h2 = hash_password("s3cret-password!"), hash_password("s3cret-password!")
    assert h1 != h2 and h1.startswith("$argon2")
    assert verify_password("s3cret-password!", h1)
    assert not verify_password("wrong", h1)
    assert not verify_password("anything", None)


def test_login_sets_httponly_session_cookie_and_returns_permissions(client, db):
    make_user(db, Role.COORDINATOR)
    res = client.post("/api/v1/auth/login", json={"email": "COORDINATOR@example.test", "password": TEST_PASSWORD})
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["role"] == "coordinator"
    assert "password_hash" not in body["user"]
    assert "donors:read" in body["permissions"] and "users:manage" not in body["permissions"]
    set_cookie = res.headers.get_list("set-cookie")
    session_cookie = next(c for c in set_cookie if c.startswith(SESSION_COOKIE))
    assert "HttpOnly" in session_cookie and "SameSite=lax" in session_cookie


def test_invalid_credentials_rejected_with_generic_message(client, db):
    make_user(db, Role.ADMIN)
    bad_pw = client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "nope"})
    no_user = client.post("/api/v1/auth/login", json={"email": "ghost@example.test", "password": "nope"})
    assert bad_pw.status_code == no_user.status_code == 401
    assert bad_pw.json() == no_user.json()
    assert db.query(AuditEvent).filter_by(action="auth.login_failed").count() == 2


def test_inactive_user_cannot_login(client, db):
    make_user(db, Role.ADMIN, is_active=False)
    res = client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": TEST_PASSWORD})
    assert res.status_code == 401


def test_login_is_rate_limited(client, db):
    make_user(db, Role.ADMIN)
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "wrong"})
    res = client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": TEST_PASSWORD})
    assert res.status_code == 429


def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_org_for_bank_manager(client, db):
    bank = make_bank(db)
    make_user(db, Role.BANK_MANAGER, bank=bank)
    login(client, "bank_manager@example.test")
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["user"]["blood_bank"]["id"] == bank.id


def test_tampered_token_rejected(client, db):
    make_user(db, Role.ADMIN)
    login(client, "admin@example.test")
    token = client.cookies.get(SESSION_COOKIE)
    client.cookies.set(SESSION_COOKIE, token[:-4] + "AAAA")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_state_changing_request_requires_csrf_header(client, db):
    make_user(db, Role.ADMIN)
    login(client, "admin@example.test")
    csrf = client.headers.pop(CSRF_HEADER)
    assert client.post("/api/v1/auth/logout").status_code == 403
    client.headers[CSRF_HEADER] = "forged"
    assert client.post("/api/v1/auth/logout").status_code == 403
    client.headers[CSRF_HEADER] = csrf
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_logout_records_audit_and_clears_cookie(client, db):
    make_user(db, Role.ADMIN)
    login(client, "admin@example.test")
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 204
    assert db.query(AuditEvent).filter_by(action="auth.logout").count() == 1


def test_security_headers_present(client):
    res = client.get("/api/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"


def test_data_status_reports_synthetic_records(client, db):
    assert client.get("/api/v1/meta/data-status").json()["demo_mode"] is False
    make_bank(db)
    body = client.get("/api/v1/meta/data-status").json()
    assert body["demo_mode"] is True and body["synthetic_records"] == 1
