from httpx import AsyncClient
from tests.conftest import TestUsers

async def get_token(client: AsyncClient, email: str, password: str) -> str:
    """Логин и возврат access-токена."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access"]

async def get_admin_token(client: AsyncClient, test_users: TestUsers) -> str:
    return await get_token(client, test_users.admin.email, "adminpass")

async def get_user_token(client: AsyncClient, test_users: TestUsers) -> str:
    return await get_token(client, test_users.user.email, "userpass")

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
