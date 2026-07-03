from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import pytest

from app.modules.accounts import AccountService, PaymentWebhookData, Account, Payment
from app.modules.users import User
from app.core.exceptions import Http404
from app.core.security import hash_password
from app.core.config import settings
from app.core.types import Money


async def test_process_payment_creates_account_and_payment(db_session: AsyncSession):
    # Подготовка: активный пользователь
    user = User(
        email="test@example.com",
        hashed_password=hash_password("12345678"),
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    service = AccountService(db_session)
    webhook_data = PaymentWebhookData(
        transaction_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        user_id=user.id,
        account_id=99,  # несуществующий external_id
        amount=Money(250),
        signature=""
    )
    # вычислим правильную подпись с нашим ключом
    fields = webhook_data.model_dump(exclude={'signature'})
    sig = AccountService._compute_webhook_signature(fields, settings.SECRET_KEY)
    webhook_data.signature = sig

    result = await service.try_process_payment(webhook_data)
    assert result is True

    # Проверяем, что счёт создался
    accounts = await service.get_user_accounts(user)
    assert len(accounts) == 1
    account = accounts[0]
    assert account.external_id == 99
    assert account.balance == 250.00

    # Проверяем платёж
    payments = await service.get_account_payments(account, user)
    assert len(payments) == 1
    assert payments[0].amount == 250.00
    assert str(payments[0].transaction_id) == "550e8400-e29b-41d4-a716-446655440000"

    # Повторный вызов должен вернуть False (дубликат transaction_id)
    result2 = await service.try_process_payment(webhook_data)
    assert result2 is False


async def test_get_user_accounts(db_session: AsyncSession):
    user = User(
        email="acc@test.com",
        hashed_password=hash_password("pass"),
        full_name="Account User",
    )
    db_session.add(user)
    await db_session.flush()

    account1 = Account(external_id=101, user_id=user.id, balance=Money(100))
    account2 = Account(external_id=102, user_id=user.id, balance=Money(200))
    db_session.add_all([account1, account2])
    await db_session.flush()

    service = AccountService(db_session)
    accounts = await service.get_user_accounts(user)

    assert len(accounts) == 2
    external_ids = {acc.external_id for acc in accounts}
    assert external_ids == {101, 102}


async def test_get_account_or_404_success(db_session: AsyncSession):
    user = User(
        email="acc2@test.com",
        hashed_password=hash_password("pass"),
        full_name="Account Owner",
    )
    db_session.add(user)
    await db_session.flush()

    account = Account(external_id=201, user_id=user.id, balance=Money(50))
    db_session.add(account)
    await db_session.flush()

    service = AccountService(db_session)
    result = await service.get_account_or_404(201, user)

    assert result.id == account.id
    assert result.external_id == 201


async def test_get_account_or_404_not_found(db_session: AsyncSession):
    user = User(
        email="acc3@test.com",
        hashed_password=hash_password("pass"),
        full_name="Another User",
    )
    db_session.add(user)
    await db_session.flush()

    service = AccountService(db_session)
    with pytest.raises(Http404):
        await service.get_account_or_404(999, user)


async def test_get_account_or_404_not_owner(db_session: AsyncSession):
    user1 = User(
        email="owner@test.com",
        hashed_password=hash_password("pass"),
        full_name="Owner",
    )
    user2 = User(
        email="other@test.com",
        hashed_password=hash_password("pass"),
        full_name="Other",
    )
    db_session.add_all([user1, user2])
    await db_session.flush()

    account = Account(external_id=301, user_id=user1.id, balance=Money(10))
    db_session.add(account)
    await db_session.flush()

    service = AccountService(db_session)
    with pytest.raises(HTTPException) as exc:
        await service.get_account_or_404(301, user2)
    assert exc.value.status_code == 403


async def test_get_account_payments(db_session: AsyncSession):
    user = User(
        email="pay@test.com",
        hashed_password=hash_password("pass"),
        full_name="Payment User",
    )
    db_session.add(user)
    await db_session.flush()

    account = Account(external_id=401, user_id=user.id, balance=Money(0))
    db_session.add(account)
    await db_session.flush()

    payment1 = Payment(
        account_id=account.id,
        amount=Money(100),
        transaction_id=UUID("12345678-1234-1234-1234-123456789abc"),
    )
    payment2 = Payment(
        account_id=account.id,
        amount=Money(200),
        transaction_id=UUID("12345678-1234-1234-1234-123456789abd"),
    )
    db_session.add_all([payment1, payment2])
    await db_session.flush()

    service = AccountService(db_session)
    payments = await service.get_account_payments(account, user)

    assert len(payments) == 2
    # Сортировка по убыванию id: последний добавленный должен быть первым
    assert payments[0].amount == 200
    assert payments[1].amount == 100


async def test_get_account_payments_not_owner(db_session: AsyncSession):
    user1 = User(
        email="payowner@test.com",
        hashed_password=hash_password("pass"),
        full_name="PayOwner",
    )
    user2 = User(
        email="payother@test.com",
        hashed_password=hash_password("pass"),
        full_name="PayOther",
    )
    db_session.add_all([user1, user2])
    await db_session.flush()

    account = Account(external_id=501, user_id=user1.id, balance=Money(0))
    db_session.add(account)
    await db_session.flush()

    service = AccountService(db_session)
    with pytest.raises(HTTPException) as exc:
        await service.get_account_payments(account, user2)
    assert exc.value.status_code == 403
