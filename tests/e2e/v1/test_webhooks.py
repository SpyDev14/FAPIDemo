from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.modules.accounts import AccountService
from app.modules.users import User
from tests.conftest import TestUsers
from tests.e2e.v1._utils import get_admin_token, auth_headers


class TestWebhook:
    async def test_webhook_success(self, client: AsyncClient, test_users: TestUsers):
        user = test_users.user
        external_id = 100
        transaction_id = str(uuid4())
        amount = "150.50"

        fields = {
            "user_id": user.id,
            "account_id": external_id,
            "transaction_id": transaction_id,
            "amount": amount,
        }
        signature = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
        payload = {**fields, "signature": signature}

        resp = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp.status_code == 200
        assert resp.json() == {"detail": "Successful processed"}

        # Проверяем создание счёта и баланс
        admin_token = await get_admin_token(client, test_users)
        accounts_resp = await client.get(
            f"/api/v1/admin/users/{user.id}/accounts",
            headers=auth_headers(admin_token)
        )
        assert accounts_resp.status_code == 200
        accounts = accounts_resp.json()
        assert len(accounts) == 1
        account = accounts[0]
        assert account["external_id"] == external_id
        assert Decimal(account["balance"]) == Decimal(amount)

        # Проверяем наличие платежа
        payments_resp = await client.get(
            f"/api/v1/admin/users/{user.id}/accounts/{external_id}/payments",
            headers=auth_headers(admin_token)
        )
        assert payments_resp.status_code == 200
        payments = payments_resp.json()
        assert len(payments) == 1
        assert Decimal(payments[0]["amount"]) == Decimal(amount)

    async def test_webhook_duplicate(self, client: AsyncClient, test_users: TestUsers, db_session: AsyncSession):
        user = test_users.user
        external_id = 200
        transaction_id = str(uuid4())
        amount = "75.00"

        fields = {
            "user_id": user.id,
            "account_id": external_id,
            "transaction_id": transaction_id,
            "amount": amount,
        }
        signature = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
        payload = {**fields, "signature": signature}

        resp1 = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp1.status_code == 200
        assert resp1.json() == {"detail": "Successful processed"}

        resp2 = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp2.status_code == 200
        assert resp2.json() == {"detail": "Processed already"}

        # Баланс не должен измениться
        admin_token = await get_admin_token(client, test_users)
        account_resp = await client.get(
            f"/api/v1/admin/users/{user.id}/accounts/{external_id}",
            headers=auth_headers(admin_token)
        )
        assert account_resp.status_code == 200
        assert Decimal(account_resp.json()["balance"]) == Decimal(amount)

    async def test_webhook_invalid_signature(self, client: AsyncClient, test_users: TestUsers):
        user = test_users.user
        external_id = 300
        transaction_id = str(uuid4())
        amount = "10.00"

        fields = {
            "user_id": user.id,
            "account_id": external_id,
            "transaction_id": transaction_id,
            "amount": amount,
        }
        signature = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
        payload = {**fields, "signature": signature + "extra"}

        resp = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp.status_code == 403
        assert "Signature is fake" in resp.text

    async def test_webhook_user_not_found(self, client: AsyncClient):
        external_id = 400
        transaction_id = str(uuid4())
        amount = "20.00"
        user_id = 99999

        fields = {
            "user_id": user_id,
            "account_id": external_id,
            "transaction_id": transaction_id,
            "amount": amount,
        }
        signature = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
        payload = {**fields, "signature": signature}

        resp = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp.status_code == 404

    async def test_webhook_account_belongs_to_other_user(self, client: AsyncClient, test_users: TestUsers, db_session: AsyncSession):
        # Создаём второго пользователя
        user2 = User(
            email="user2@test.com",
            hashed_password=hash_password("password12345"),
            full_name="User Two",
            is_active=True,
            role=User.Role.USER,
        )
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user2)

        # Создаём счёт для первого пользователя
        from app.modules.accounts import Account
        external_id = 500
        account = Account(external_id=external_id, user_id=test_users.user.id, balance=Decimal("0"))
        db_session.add(account)
        await db_session.commit()

        # Отправляем вебхук от имени второго пользователя
        transaction_id = str(uuid4())
        amount = "30.00"
        fields = {
            "user_id": user2.id,
            "account_id": external_id,
            "transaction_id": transaction_id,
            "amount": amount,
        }
        signature = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
        payload = {**fields, "signature": signature}

        resp = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp.status_code == 400
        assert "not belong" in resp.text

    async def test_webhook_creates_account_if_not_exists(self, client: AsyncClient, test_users: TestUsers):
        user = test_users.user
        external_id = 600
        transaction_id = str(uuid4())
        amount = "42.00"

        fields = {
            "user_id": user.id,
            "account_id": external_id,
            "transaction_id": transaction_id,
            "amount": amount,
        }
        signature = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
        payload = {**fields, "signature": signature}

        resp = await client.post("/api/v1/webhooks/payment", json=payload)
        assert resp.status_code == 200

        admin_token = await get_admin_token(client, test_users)
        account_resp = await client.get(
            f"/api/v1/admin/users/{user.id}/accounts/{external_id}",
            headers=auth_headers(admin_token)
        )
        assert account_resp.status_code == 200
        assert Decimal(account_resp.json()["balance"]) == Decimal(amount)
