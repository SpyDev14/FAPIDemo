from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts import AccountService, PaymentWebhookData
from app.modules.users import User
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
