"""
Priority 1 tests: JWT verification and ownership boundaries.

These cover the security-critical surface called out in the code review:
_decode_supabase_jwt, require_auth, require_run_access, require_pokemon_access.

JWT decode tests run for real (no DB needed). The require_* tests mock the
DB-backed ownership lookups (run_belongs_to_user / pokemon_belongs_to_user)
since the goal here is to verify the authorization *logic*, not the SQL --
the SQL itself is covered by the Priority 2 integration tests.
"""
import time

import jwt
import pytest

import api as api_module


# ---------------------------------------------------------------------------
# _decode_supabase_jwt
# ---------------------------------------------------------------------------

def make_hs256_token(secret, *, sub="user-123", email="riley@example.com",
                      audience="authenticated", expires_in=3600, extra_claims=None):
    payload = {
        "sub": sub,
        "email": email,
        "aud": audience,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_decode_valid_hs256_token_returns_payload(hs256_secret):
    token = make_hs256_token(hs256_secret)
    payload = api_module._decode_supabase_jwt(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "riley@example.com"


def test_decode_expired_token_returns_none(hs256_secret):
    token = make_hs256_token(hs256_secret, expires_in=-10)
    assert api_module._decode_supabase_jwt(token) is None


def test_decode_tampered_signature_returns_none(hs256_secret):
    token = make_hs256_token(hs256_secret)
    # Corrupt a character in the middle of the signature segment -- avoid the
    # last character, which (due to base64url padding bits) doesn't always
    # change the underlying signature bytes when flipped.
    header, payload, signature = token.split(".")
    mid = len(signature) // 2
    flipped_char = "A" if signature[mid] != "A" else "B"
    bad_signature = signature[:mid] + flipped_char + signature[mid + 1:]
    tampered = f"{header}.{payload}.{bad_signature}"
    assert api_module._decode_supabase_jwt(tampered) is None


def test_decode_wrong_secret_returns_none(hs256_secret):
    token = make_hs256_token("a-completely-different-secret")
    assert api_module._decode_supabase_jwt(token) is None


def test_decode_garbage_token_returns_none(hs256_secret):
    assert api_module._decode_supabase_jwt("not-a-real-jwt") is None


def test_decode_missing_secret_falls_through_to_jwks(monkeypatch):
    # No SUPABASE_JWT_SECRET set: should attempt the JWKS path and fail
    # gracefully (no network in tests) rather than raising.
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SUPRABASE_JWT_SECRET", raising=False)
    token = make_hs256_token("irrelevant-secret")
    assert api_module._decode_supabase_jwt(token) is None


# ---------------------------------------------------------------------------
# get_current_user / require_auth
# ---------------------------------------------------------------------------

def test_get_current_user_no_auth_header(app):
    with app.test_request_context("/api/runs"):
        assert api_module.get_current_user() is None


def test_get_current_user_malformed_header(app):
    with app.test_request_context("/api/runs", headers={"Authorization": "NotBearer abc"}):
        assert api_module.get_current_user() is None


def test_get_current_user_invalid_token(app):
    with app.test_request_context("/api/runs", headers={"Authorization": "Bearer garbage"}):
        assert api_module.get_current_user() is None


def test_get_current_user_valid_token_looks_up_user(app, hs256_secret, monkeypatch):
    token = make_hs256_token(hs256_secret, sub="supabase-abc", email="riley@example.com")
    fake_user = {"user_id": 42, "email": "riley@example.com"}

    captured = {}

    def fake_get_or_create_user(conn, supabase_id, email=None):
        captured["supabase_id"] = supabase_id
        captured["email"] = email
        return fake_user

    monkeypatch.setattr(api_module, "get_or_create_user_by_supabase_id", fake_get_or_create_user)
    monkeypatch.setattr(api_module, "get_db", lambda: "fake-conn")

    with app.test_request_context("/api/runs", headers={"Authorization": f"Bearer {token}"}):
        user = api_module.get_current_user()

    assert user == fake_user
    assert captured["supabase_id"] == "supabase-abc"
    assert captured["email"] == "riley@example.com"


def test_require_auth_returns_401_when_unauthenticated(app, monkeypatch):
    monkeypatch.setattr(api_module, "get_current_user", lambda: None)
    with app.test_request_context("/api/runs"):
        user, error = api_module.require_auth()
    assert user is None
    assert error is not None
    response, status = error
    assert status == 401


def test_require_auth_returns_user_when_authenticated(app, monkeypatch):
    fake_user = {"user_id": 1}
    monkeypatch.setattr(api_module, "get_current_user", lambda: fake_user)
    with app.test_request_context("/api/runs"):
        user, error = api_module.require_auth()
    assert user == fake_user
    assert error is None


# ---------------------------------------------------------------------------
# require_run_access / require_pokemon_access (ownership boundary)
# ---------------------------------------------------------------------------

def test_require_run_access_denies_non_owner(app, monkeypatch):
    """User A must not be able to access user B's run."""
    user_a = {"user_id": 1}
    monkeypatch.setattr(api_module, "get_current_user", lambda: user_a)
    monkeypatch.setattr(api_module, "run_belongs_to_user", lambda conn, run_id, user_id: False)

    with app.test_request_context("/api/runs/99/1"):
        user, error = api_module.require_run_access("fake-conn", 99)

    assert error is not None
    response, status = error
    assert status == 404, "ownership failures should look like 404s, not leak existence via 403"


def test_require_run_access_allows_owner(app, monkeypatch):
    user_a = {"user_id": 1}
    monkeypatch.setattr(api_module, "get_current_user", lambda: user_a)
    monkeypatch.setattr(api_module, "run_belongs_to_user", lambda conn, run_id, user_id: True)

    with app.test_request_context("/api/runs/99/1"):
        user, error = api_module.require_run_access("fake-conn", 99)

    assert error is None
    assert user == user_a


def test_require_run_access_requires_authentication_first(app, monkeypatch):
    monkeypatch.setattr(api_module, "get_current_user", lambda: None)
    ownership_called = {"called": False}

    def fake_run_belongs_to_user(*args, **kwargs):
        ownership_called["called"] = True
        return True

    monkeypatch.setattr(api_module, "run_belongs_to_user", fake_run_belongs_to_user)

    with app.test_request_context("/api/runs/99/1"):
        user, error = api_module.require_run_access("fake-conn", 99)

    response, status = error
    assert status == 401
    assert ownership_called["called"] is False, "should short-circuit on auth before checking ownership"


def test_require_pokemon_access_denies_non_owner(app, monkeypatch):
    user_a = {"user_id": 1}
    monkeypatch.setattr(api_module, "get_current_user", lambda: user_a)
    monkeypatch.setattr(api_module, "pokemon_belongs_to_user", lambda conn, pokemon_id, user_id: False)

    with app.test_request_context("/api/pokebank/55"):
        user, error = api_module.require_pokemon_access("fake-conn", 55)

    response, status = error
    assert status == 404


def test_require_pokemon_access_allows_owner(app, monkeypatch):
    user_a = {"user_id": 1}
    monkeypatch.setattr(api_module, "get_current_user", lambda: user_a)
    monkeypatch.setattr(api_module, "pokemon_belongs_to_user", lambda conn, pokemon_id, user_id: True)

    with app.test_request_context("/api/pokebank/55"):
        user, error = api_module.require_pokemon_access("fake-conn", 55)

    assert error is None
    assert user == user_a
