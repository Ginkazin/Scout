from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from uuid import UUID, uuid4

import jwt
import pytest
import pytest_asyncio
from passlib.exc import PasswordTruncateError
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import decode_token, hash_password, verify_password
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole


async def test_register_user(
    client,
    db_session,
    free_plan,
):
    response = await client.post(
        "/auth/register",
        json={
            "name": "João Teste",
            "email": "joao@teste.com",
            "password": "Senha@123",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "João Teste"
    assert data["email"] == "joao@teste.com"
    assert "password" not in data
    assert "password_hash" not in data

    result = await db_session.execute(
        select(User).where(
            User.email == "joao@teste.com"
        )
    )

    user = result.scalar_one_or_none()

    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != "Senha@123"
    assert verify_password("Senha@123", user.password_hash)
    assert user.role == UserRole.ADMIN
    assert data["role"] == "ADMIN"

    result = await db_session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id
        )
    )

    subscription = result.scalar_one_or_none()

    assert subscription is not None
    assert subscription.plan_id == free_plan.id
    assert subscription.status == SubscriptionStatus.ACTIVE

async def test_register_email_duplicate(client, free_plan):
    payload = {
        "name": "João Teste",
        "email": "joao@teste.com",
        "password": "Senha@123",
    }

    first_response = await client.post(
        "/auth/register",
        json=payload
    )

    second_response = await client.post(
        "/auth/register",
        json=payload
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Email já cadastrado"

async def test_register_password_strength(client, free_plan):
    weak_password_payload = {
        "name": "João Teste",
        "email": "joao@teste.com",
        "password": "Bi123@"
    }

    weak_password_payload2 = {
        "name": "João Teste",
        "email": "joao2@teste.com",
        "password": "Bielrau@"
    }

    weak_password_payload3 = {
        "name": "João Teste",
        "email": "joao3@teste.com",
        "password": "biel123@"
    }

    weak_password_payload4 = {
        "name": "João Teste",
        "email": "joao4@teste.com",
        "password": "BIEL123@"
    }

    weak_password_payload5 = {
        "name": "João Teste",
        "email": "joao5@teste.com",
        "password": "Biel1234"
    }

    weak_password_payload6 = {
        "name": "João Teste",
        "email": "joao6@teste.com",
        "password": "Biel123@"
    }

    response = await client.post(
        "/auth/register",
        json=weak_password_payload
    )

    response2 = await client.post(
        "/auth/register",
        json=weak_password_payload2
    )

    response3 = await client.post(
        "/auth/register",
        json=weak_password_payload3
    )

    response4 = await client.post(
        "/auth/register",
        json=weak_password_payload4
    )

    response5 = await client.post(
        "/auth/register",
        json=weak_password_payload5
    )

    response6 = await client.post(
        "/auth/register",
        json=weak_password_payload6
    )

    assert response.status_code == 422
    assert response2.status_code == 422
    assert response3.status_code == 422
    assert response4.status_code == 422
    assert response5.status_code == 422
    assert response6.status_code == 201

    assert response.json()["detail"][0]["type"] == "string_too_short"
    assert "A senha deve conter pelo menos um número." in response2.json()["detail"][0]["msg"]
    assert "A senha deve conter pelo menos uma letra maiúscula." in response3.json()["detail"][0]["msg"]
    assert "A senha deve conter pelo menos uma letra minúscula." in response4.json()["detail"][0]["msg"]
    assert "A senha deve conter pelo menos um caractere especial." in response5.json()["detail"][0]["msg"]
    assert response6.json()["name"] == "João Teste"

async def test_login_user(client, db_session, free_plan):
    register_payload = {
        "name": "João Teste2",
        "email": "joao2@teste.com",
        "password": "Senha@123",
    }

    register_response = await client.post(
        "/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201

    login_payload = {
        "email": "joao2@teste.com",
        "password": "Senha@123",
    }

    login_response = await client.post(
        "/auth/login",
        json=login_payload
    )

    assert login_response.status_code == 200

    body = login_response.json()

    assert "access_token" in body
    assert body["access_token"] != ""
    assert body["token_type"] == "Bearer"

    assert "refresh_token" in login_response.cookies
    refresh_token = login_response.cookies["refresh_token"]
    assert refresh_token != ""

async def test_login_user_password_incorrect(client, db_session, free_plan):
    register_payload = {
        "name": "João Teste3",
        "email": "joao3@teste.com",
        "password": "Senha@123",
    }

    register_response = await client.post(
        "/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201

    login_payload = {
        "email": "joao3@teste.com",
        "password": "Senha@1234",  # Incorrect password
    }

    login_response = await client.post(
        "/auth/login",
        json=login_payload
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Email ou senha inválidos"

async def test_login_user_incorrect_email(client, db_session, free_plan):
    register_payload = {
        "name": "João Teste4",
        "email": "joao4@teste.com",
        "password": "Senha@123",
    }

    register_response = await client.post(
        "/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201

    login_payload = {
        "email": "joao5@teste.com",
        "password": "Senha@123",
    }

    login_response = await client.post(
        "/auth/login",
        json=login_payload
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Email ou senha inválidos"

async def test_login_user_inactive(client, db_session, free_plan):
    register_payload = {
        "name": "João Teste5",
        "email": "joao5@teste.com",
        "password": "Senha@123",
    }

    register_response = await client.post(
        "/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    session = await db_session.get(User, user_id)
    session.is_active = False
    await db_session.commit()

    login_payload = {
        "email": "joao5@teste.com",
        "password": "Senha@123",
    }

    login_response = await client.post(
        "/auth/login",
        json=login_payload
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Email ou senha inválidos"

async def test_refresh_token(client, db_session, free_plan):
    register_payload = {
        "name": "João Teste6",
        "email": "joao6@teste.com",
        "password": "Senha@123",
    }

    register_response = await client.post(
        "/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201

    login_payload = {
        "email": "joao6@teste.com",
        "password": "Senha@123",
    }

    login_response = await client.post(
        "/auth/login",
        json=login_payload
    )

    assert login_response.status_code == 200
    assert "refresh_token" in login_response.cookies
    assert login_response.cookies["refresh_token"] != ""

    refresh_response = await client.post("/auth/refresh")

    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


# Fixtures locais: exercitam o registro/login reais, sem substituir autenticação.
@pytest_asyncio.fixture
async def registered_user(client, db_session, free_plan):
    response = await client.post(
        "/auth/register",
        json={"name": "Auth Teste", "email": "auth@example.com", "password": "Senha@123"},
    )
    assert response.status_code == 201, response.text
    return await db_session.get(User, UUID(response.json()["id"]))


@pytest_asyncio.fixture
async def authenticated_user(client, registered_user):
    response = await client.post(
        "/auth/login", json={"email": registered_user.email, "password": "Senha@123"}
    )
    assert response.status_code == 200, response.text
    return registered_user, response


async def assert_no_accounts(db_session):
    for model in (User, Subscription):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("extra", [{"role": "OWNER"}, {"role": "MEMBER"}, {"is_active": False}])
async def test_register_rejects_privileged_fields(client, db_session, free_plan, extra):
    response = await client.post(
        "/auth/register",
        json={"name": "Auth Teste", "email": "auth@example.com", "password": "Senha@123", **extra},
    )
    assert response.status_code == 422, response.text
    await assert_no_accounts(db_session)


@pytest.mark.parametrize("inactive_plan", [False, True], ids=["missing", "inactive"])
async def test_register_requires_available_free_plan(client, db_session, inactive_plan):
    if inactive_plan:
        from app.models.plan import Plan

        db_session.add(Plan(name="FREE", is_active=False))
        await db_session.flush()
    response = await client.post(
        "/auth/register",
        json={"name": "Auth Teste", "email": "auth@example.com", "password": "Senha@123"},
    )
    assert response.status_code == 500, response.text
    await assert_no_accounts(db_session)


async def test_email_normalization_and_case_insensitive_duplicate(client, db_session, free_plan):
    payload = {"name": "Auth Teste", "email": "AUTH@EXAMPLE.COM", "password": "Senha@123"}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "auth@example.com"
    duplicate = await client.post("/auth/register", json={**payload, "email": "auth@example.com"})
    assert duplicate.status_code == 409
    login = await client.post("/auth/login", json={"email": "Auth@Example.com", "password": "Senha@123"})
    assert login.status_code == 200, login.text
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("password", ["Aa1!" + "x" * 68, "Aa1!" + "é" * 34], ids=["ascii", "unicode"])
async def test_password_exactly_72_bytes_can_register_and_login(client, free_plan, password):
    assert len(password.encode("utf-8")) == 72
    response = await client.post(
        "/auth/register", json={"name": "Auth Teste", "email": "auth@example.com", "password": password}
    )
    assert response.status_code == 201, response.text
    login = await client.post("/auth/login", json={"email": "auth@example.com", "password": password})
    assert login.status_code == 200, login.text
    # Mesmo prefixo de 72 bytes não pode autenticar com um sufixo adicional.
    client.cookies.clear()
    rejected = await client.post(
        "/auth/login", json={"email": "auth@example.com", "password": password + "x"}
    )
    assert rejected.status_code == 401
    assert "refresh_token" not in rejected.cookies


@pytest.mark.parametrize("password", ["Aa1!" + "x" * 69, "Aa1!" + "é" * 35], ids=["ascii", "unicode"])
async def test_register_rejects_password_over_72_bytes(client, db_session, free_plan, password):
    assert len(password) <= 128
    assert len(password.encode("utf-8")) > 72
    response = await client.post(
        "/auth/register", json={"name": "Auth Teste", "email": "auth@example.com", "password": password}
    )
    assert response.status_code == 422, response.text
    await assert_no_accounts(db_session)


def test_hash_password_does_not_silently_truncate():
    with pytest.raises(PasswordTruncateError):
        hash_password("Aa1!" + "x" * 69)


async def test_login_updates_last_login(client, db_session, registered_user):
    assert registered_user.last_login is None
    before = datetime.now(timezone.utc)
    response = await client.post(
        "/auth/login", json={"email": registered_user.email, "password": "Senha@123"}
    )
    after = datetime.now(timezone.utc)
    assert response.status_code == 200
    await db_session.refresh(registered_user)
    assert before <= registered_user.last_login <= after


async def test_failed_login_does_not_issue_tokens_or_update_last_login(client, db_session, registered_user):
    response = await client.post(
        "/auth/login", json={"email": registered_user.email, "password": "Wrong@123"}
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.cookies
    await db_session.refresh(registered_user)
    assert registered_user.last_login is None


async def test_login_token_claims_and_cookie_attributes(authenticated_user):
    user, response = authenticated_user
    body = response.json()
    assert "refresh_token" not in body
    assert "password" not in body
    assert "password_hash" not in body
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    refresh_cookie = cookie["refresh_token"]
    assert refresh_cookie["httponly"]
    assert refresh_cookie["samesite"].lower() == "lax"
    assert refresh_cookie["path"] == "/auth"
    assert int(refresh_cookie["max-age"]) > 0
    for token, token_type, lifetime in (
        (body["access_token"], "access", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        (refresh_cookie.value, "refresh", settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400),
    ):
        claims = decode_token(token)
        assert claims["sub"] == str(user.id)
        assert claims["type"] == token_type
        assert claims["exp"] - claims["iat"] == lifetime


async def test_access_and_refreshed_access_work_on_protected_endpoint(client, authenticated_user):
    user, login = authenticated_user
    token = login.json()["access_token"]
    response = await client.get("/customers", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    assert response.json() == []
    refreshed = await client.post("/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    assert "refresh_token" not in refreshed.json()
    assert refreshed.json()["token_type"] == "Bearer"
    token = refreshed.json()["access_token"]
    assert decode_token(token)["sub"] == str(user.id)
    assert decode_token(token)["type"] == "access"
    response = await client.get("/customers", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint", ["access", "refresh"])
@pytest.mark.parametrize(
    "case", ["missing", "malformed", "expired", "wrong-signature", "wrong-type", "missing-sub", "invalid-sub", "unknown-user"]
)
async def test_auth_rejects_invalid_credentials(client, registered_user, endpoint, case):
    now = datetime.now(timezone.utc)
    claims = {"sub": str(registered_user.id), "type": endpoint, "iat": now, "exp": now + timedelta(minutes=5)}
    key = settings.SECRET_KEY.get_secret_value()
    if case == "expired":
        claims.update(iat=now - timedelta(minutes=10), exp=now - timedelta(minutes=5))
    elif case == "wrong-signature":
        key = "incorrect-signing-key-for-auth-tests-0000000000000000000"
    elif case == "wrong-type":
        claims["type"] = "refresh" if endpoint == "access" else "access"
    elif case == "missing-sub":
        del claims["sub"]
    elif case == "invalid-sub":
        claims["sub"] = "not-a-uuid"
    elif case == "unknown-user":
        claims["sub"] = str(uuid4())
    token = "not-a-jwt" if case == "malformed" else jwt.encode(claims, key, algorithm=settings.ALGORITHM)
    client.cookies.clear()
    if endpoint == "refresh":
        if case != "missing":
            client.cookies.set("refresh_token", token, path="/auth")
        response = await client.post("/auth/refresh")
    else:
        headers = {} if case == "missing" else {"Authorization": f"Bearer {token}"}
        response = await client.get("/customers", headers=headers)
    assert response.status_code == 401, response.text
    assert "access_token" not in response.json()


@pytest.mark.parametrize("endpoint", ["access", "refresh"])
async def test_existing_tokens_rejected_after_user_disabled(client, db_session, authenticated_user, endpoint):
    user, login = authenticated_user
    user.is_active = False
    await db_session.flush()
    if endpoint == "refresh":
        response = await client.post("/auth/refresh")
    else:
        response = await client.get(
            "/customers", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
        )
    assert response.status_code == 401, response.text


async def test_logout_clears_cookie_and_prevents_cookie_refresh(client, authenticated_user):
    assert client.cookies.get("refresh_token")
    response = await client.post("/auth/logout")
    assert response.status_code == 204
    assert response.content == b""
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    assert cookie["refresh_token"]["path"] == "/auth"
    assert cookie["refresh_token"]["max-age"] == "0"
    assert client.cookies.get("refresh_token") is None
    refreshed = await client.post("/auth/refresh")
    assert refreshed.status_code == 401


async def test_logout_without_cookie_is_idempotent(client):
    for _ in range(2):
        response = await client.post("/auth/logout")
        assert response.status_code == 204
        assert response.content == b""
