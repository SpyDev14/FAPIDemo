from httpx import AsyncClient
import pytest

from tests.e2e.v1._utils import get_user_token, auth_headers
from tests.conftest import TestUsers


class TestUserEndpoints:
    async def test_get_me(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/users/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_users.user.email
        assert data["full_name"] == test_users.user.full_name
        assert "id" in data

    async def test_get_my_accounts_empty(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/users/me/accounts", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_my_account_detail_not_found(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/users/me/accounts/999", headers=auth_headers(token))
        assert resp.status_code == 404

    async def test_get_my_account_payments_not_found(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/users/me/accounts/999/payments", headers=auth_headers(token))
        assert resp.status_code == 404


class TestUserEndpointsUnauthorized:
    """Проверка, что без токена доступ к пользовательским эндпоинтам запрещён (401)."""

    async def test_get_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401

    async def test_get_my_accounts_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me/accounts")
        assert resp.status_code == 401

    async def test_get_my_account_detail_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me/accounts/1")
        assert resp.status_code == 401

    async def test_get_my_account_payments_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me/accounts/1/payments")
        assert resp.status_code == 401
