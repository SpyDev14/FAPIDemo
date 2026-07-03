from httpx import AsyncClient

from tests.conftest import TestUsers
from tests.e2e.v1._utils import get_admin_token, get_user_token, auth_headers


class TestAdminEndpointsByAdmin:
    async def test_get_users(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        resp = await client.get("/api/v1/admin/users", headers=auth_headers(token))
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) >= 2
        emails = [u["email"] for u in users]
        assert test_users.admin.email in emails
        assert test_users.user.email in emails

    async def test_create_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        payload = {
            "email": "new@test.com",
            "password": "newpass123",
            "full_name": "New User",
        }
        resp = await client.post("/api/v1/admin/users", json=payload, headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@test.com"
        assert data["full_name"] == "New User"
        assert "id" in data

    async def test_get_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        user_id = test_users.user.id
        resp = await client.get(f"/api/v1/admin/users/{user_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_users.user.email
        assert data["full_name"] == test_users.user.full_name
        assert data["is_active"] is True
        assert "accounts" in data

    async def test_update_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        user_id = test_users.user.id
        payload = {"full_name": "Updated Name", "is_active": False}
        resp = await client.patch(f"/api/v1/admin/users/{user_id}", json=payload, headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Updated Name"

        # Проверяем, что изменения сохранились
        resp2 = await client.get(f"/api/v1/admin/users/{user_id}", headers=auth_headers(token))
        assert resp2.json()["full_name"] == "Updated Name"
        assert resp2.json()["is_active"] is False

    async def test_delete_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        # Создаём пользователя для удаления
        create_resp = await client.post("/api/v1/admin/users", json={
            "email": "todelete@test.com",
            "password": "password123",
            "full_name": "To Delete",
        }, headers=auth_headers(token))
        user_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/admin/users/{user_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == {"detail": "User deactivated"}

        get_resp = await client.get(f"/api/v1/admin/users/{user_id}", headers=auth_headers(token))
        assert not get_resp.json()["is_active"]

    async def test_get_user_accounts(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        user_id = test_users.user.id
        resp = await client.get(f"/api/v1/admin/users/{user_id}/accounts", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_user_account_not_found(self, client: AsyncClient, test_users: TestUsers):
        token = await get_admin_token(client, test_users)
        user_id = test_users.user.id
        resp = await client.get(f"/api/v1/admin/users/{user_id}/accounts/999", headers=auth_headers(token))
        assert resp.status_code == 404


class TestAdminEndpointsUnauthorized:
    """Проверка, что без токена доступ к админским эндпоинтам запрещён (401)."""

    async def test_get_users_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/users")
        assert resp.status_code == 401

    async def test_create_user_no_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/admin/users", json={})
        assert resp.status_code == 401

    async def test_get_user_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/users/1")
        assert resp.status_code == 401

    async def test_update_user_no_token(self, client: AsyncClient):
        resp = await client.patch("/api/v1/admin/users/1", json={})
        assert resp.status_code == 401

    async def test_delete_user_no_token(self, client: AsyncClient):
        resp = await client.delete("/api/v1/admin/users/1")
        assert resp.status_code == 401

    async def test_get_user_accounts_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/users/1/accounts")
        assert resp.status_code == 401

    async def test_get_user_account_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/users/1/accounts/1")
        assert resp.status_code == 401

    async def test_get_account_payments_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/users/1/accounts/1/payments")
        assert resp.status_code == 401

    async def test_get_account_payment_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/users/1/accounts/1/payments/1")
        assert resp.status_code == 401


class TestAdminEndpointsByUser:
    """Проверка, что обычный пользователь не имеет доступа к админским эндпоинтам (403)."""

    async def test_get_users_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/admin/users", headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_create_user_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.post("/api/v1/admin/users", json={}, headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_get_user_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/admin/users/1", headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_update_user_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.patch("/api/v1/admin/users/1", json={}, headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_delete_user_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.delete("/api/v1/admin/users/1", headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_get_user_accounts_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/admin/users/1/accounts", headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_get_user_account_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/admin/users/1/accounts/1", headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_get_account_payments_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/admin/users/1/accounts/1/payments", headers=auth_headers(token))
        assert resp.status_code == 403

    async def test_get_account_payment_by_user(self, client: AsyncClient, test_users: TestUsers):
        token = await get_user_token(client, test_users)
        resp = await client.get("/api/v1/admin/users/1/accounts/1/payments/1", headers=auth_headers(token))
        assert resp.status_code == 403
