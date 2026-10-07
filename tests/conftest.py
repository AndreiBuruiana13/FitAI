pytest_plugins = "pytest_asyncio"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app import main, database


def pytest_configure(config):
    database.init_db("sqlite:///:memory:")


@pytest_asyncio.fixture(scope="session")
async def async_client():
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def auth_token(async_client):
    res = await async_client.post(
        "/register",
        json={"email": "fixture@test.com", "password": "fixturepass123"},
    )
    return res.json()["access_token"]
