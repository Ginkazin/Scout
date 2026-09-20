from sqlalchemy import select
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User


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