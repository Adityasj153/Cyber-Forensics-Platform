import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "role": "investigator",
        },
    )
    assert reg_resp.status_code == 201
    user = reg_resp.json()
    assert user["username"] == "testuser"
    assert user["role"] == "investigator"

    # Login
    login_resp = await client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123",
        },
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data

    # Get me
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = await client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_create_case(client):
    # Register and login
    await client.post(
        "/api/auth/register",
        json={
            "username": "casecreator",
            "email": "creator@example.com",
            "password": "pass123",
            "role": "investigator",
        },
    )
    login_resp = await client.post(
        "/api/auth/login",
        json={
            "username": "casecreator",
            "password": "pass123",
        },
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create case
    case_resp = await client.post(
        "/api/cases",
        json={
            "name": "Test Investigation",
            "description": "Testing case creation",
        },
        headers=headers,
    )
    assert case_resp.status_code == 201
    case = case_resp.json()
    assert case["name"] == "Test Investigation"
    assert case["status"] == "open"

    # List cases
    list_resp = await client.get("/api/cases", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
