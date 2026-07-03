from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
import pytest

from app.modules.auth import AuthTokens

from tests.conftest import TestUsers


@pytest.mark.asyncio
class TestAuth:
    async def test_login_success(self, client: AsyncClient, test_users: TestUsers):
        resp = await client.post("/api/v1/auth/login", json={
            "email": test_users.user.email,
            "password": "userpass"
        })
        assert resp.status_code == 200
        tokens = AuthTokens(**resp.json())
        assert tokens.access
        assert tokens.refresh

    async def test_login_fail_wrong_password(self, client: AsyncClient, test_users: TestUsers):
        resp = await client.post("/api/v1/auth/login", json={
            "email": test_users.user.email,
            "password": "wrong"
        })
        assert resp.status_code == 401

    async def test_login_fail_inactive_user(self, client: AsyncClient, db_session: AsyncSession, test_users: TestUsers):
        user = test_users.user
        user.is_active = False
        await db_session.commit()
        resp = await client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": "userpass"
        })
        assert resp.status_code == 401

    async def test_refresh_success(self, client: AsyncClient, test_users: TestUsers):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": test_users.user.email,
            "password": "userpass"
        })
        refresh_token = login_resp.json()["refresh"]
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        tokens = AuthTokens(**resp.json())
        assert tokens.access
        assert tokens.refresh

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
        assert resp.status_code == 401
