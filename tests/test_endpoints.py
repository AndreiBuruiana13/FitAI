import pytest
from datetime import date


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_success(async_client):
    res = await async_client.post(
        "/register",
        json={"email": "new_user@test.com", "password": "strongpass123"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client):
    payload = {"email": "duplicate@test.com", "password": "strongpass123"}
    await async_client.post("/register", json=payload)
    res = await async_client.post("/register", json=payload)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_register_short_password(async_client):
    res = await async_client.post(
        "/register",
        json={"email": "short@test.com", "password": "short"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    await async_client.post(
        "/register",
        json={"email": "wrongpass@test.com", "password": "correctpass123"},
    )
    res = await async_client.post(
        "/login",
        data={"username": "wrongpass@test.com", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code in (400, 401)


@pytest.mark.asyncio
async def test_recovery_log_and_retrieve(async_client, auth_token):
    today = date.today().isoformat()
    log_res = await async_client.post(
        "/recovery/log",
        json={"date": today, "sleep_hours": 7.5, "resting_heart_rate": 62, "muscle_soreness": 3.0},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert log_res.status_code == 200

    trend_res = await async_client.get(
        "/recovery/trend?days=30",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert trend_res.status_code == 200
    assert today in trend_res.json()["dates"]


@pytest.mark.asyncio
async def test_recovery_log_invalid_date(async_client, auth_token):
    res = await async_client.post(
        "/recovery/log",
        json={"date": "not-a-date", "sleep_hours": 7.0},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_recovery_seed_creates_30_days(async_client):
    res = await async_client.post(
        "/register",
        json={"email": "phase2@test.com", "password": "StrongPass123"},
    )
    token = res.json()["access_token"]

    seed_res = await async_client.post(
        "/recovery/seed",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert seed_res.status_code == 200
    assert seed_res.json()["count"] == 90
