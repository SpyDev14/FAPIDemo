from datetime import datetime
from decimal  import Decimal
from uuid     import UUID
import hashlib, hmac, logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import (
    BigInteger, Numeric, DateTime,
    ForeignKey, func, select, update
)
from pydantic import BaseModel, Field
from fastapi import Depends, status, HTTPException

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.fk_on_delete         import CASCADE
from app.utils.orm.shortcuts            import get_or_404, get_or_create
from app.utils.fastapi.deps             import AppScopeDependency
from app.modules.user                   import ExistsUser, User, UserService, get_user_service
from app.core.database                  import Base, AsyncDBSession
from app.core.config                    import settings

_logger = logging.getLogger(__name__)

### Models ###
# Base.type_annotation_map было бы оверинженерингом для этого,
# поэтому я выбрал простой алиас через переменную (чтобы была
# согласованность)
# Если эти двое (модели) будут разбиты на разные модули, можно
# будет создать модуль с типами и добавить его в annotation_map
_Money = Numeric(15, 2)
class Account(Base):
    __tablename__ = 'accounts'

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey('users.id', ondelete=CASCADE), index=True,
    )
    user: Mapped[User] = relationship(User, back_populates='accounts')
    # ID from external payment system
    external_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    balance: Mapped[Decimal] = mapped_column(_Money, default=Decimal('0.00'))

    payments: Mapped[list['Payment']] = relationship(
        'Payment', back_populates='account', cascade=ALL_AND_DELETE_ORPHAN,
    )

class Payment(Base):
    __tablename__ = 'payments'

    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Account.id, ondelete=CASCADE), index=True,
    )
    account: Mapped[Account] = relationship(Account, back_populates='payments')
    amount: Mapped[Decimal] = mapped_column(_Money)
    transaction_id: Mapped[UUID] = mapped_column(unique=True)

    # Обычно мы будем сортировать эти записи в порядке "сначала новые",
    # но так как id увеличивается с каждой новой записью, сортировка
    # будет вестись не по created_at, а по уменьшению id, так как я не
    # хочу создавать лишний индекс (это не имеет смысла). Поэтому поле
    # используется только для хранения данных.
    # Всем известная информация: индексы занимают много места на диске,
    # замедляют UPDATE & INSERT, взамен ускоряя все операции по полю
    # (такие как фильтрация, сортировка, JOIN-ы и так далее). Поэтому
    # каждый индекс должен быть оправдан и необходим, каждое поле по
    # которому мы часто производим операции должно быть индексировано.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now())

### Schemas ###
# [Account]
class AccountRead(BaseModel):
    id: int = Field(alias='external_id')
    balance: Decimal

# [Payment]
class PaymentRead(BaseModel):
    amount: Decimal
    created_at: datetime

class PaymentWebhookData(BaseModel):
    user_id: int
    account_id: int
    transaction_id: str
    amount: int
    signature: str

### Services ###
class AccountService:
    def __init__(self, user_service: UserService):
        self._user_service = user_service

    def _compute_webhook_signature(self, data: PaymentWebhookData, secret_key: str):
        # В сторонней системе подпись генерируется как SHA256 хеш строки,
        # полученной путём конкатенации строковых представлений всех значений,
        # отсортированных в алфавитном порядке по названию и с добавленным на конце
        # SECRET_KEY. Например, для словаря user_id, account_id,
        # transaction_id и amount строка для сигнатуры будет выглядеть как:
        # f"{account_id}{amount}{transaction_id}{user_id}{secret_key}"
        data_dict = data.model_dump(exclude={'signature'})
        signature_string = ''.join(str(data_dict[k]) for k in sorted(data_dict.keys())) + secret_key
        return hashlib.sha256(signature_string.encode()).hexdigest()

    def _verify_webhook_signature(self, data: PaymentWebhookData) -> bool:
        expected_signature = self._compute_webhook_signature(data, settings.SECRET_KEY)

        # NOTE: Используйте hmac.compare вместо `==` потому-что он защищён от тайминг-атак
        return hmac.compare_digest(expected_signature, data.signature)

    async def _get_or_create_account(
            self, external_id: int, user: ExistsUser, db: AsyncDBSession
        ) -> tuple[Account, bool]:
        return await get_or_create(
            select(Account).where(Account.user_id == user.id),
            Account(user_id = user.id, external_id = external_id),
            db
        )

    async def _change_account_balance(self, account_id: int, amount: int, db: AsyncDBSession):
        """
        Изменяет баланс по переданному id на переданную сумму. Сумма (`amount`) **может быть отрицательной**.
        """
        await db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(balance = Account.balance + amount) # Атомарное изменение баланса чтобы из-за RC деньги не исчезли
        )

    async def try_process_payment(self, data: PaymentWebhookData, db: AsyncDBSession) -> bool:
        """
        Возвращает `True`, если было обработано и `False`, если оплата уже была обработана.

        ВАЖНО: вызывает rollback на текущей сессии, начинает **новую**
        транзакцию (BEGIN), делает коммит в случае успеха.

        Raises:
            Http404: Пользователь не найден
            HTTPException: Сигнатура сфальсифицирована
        """
        if not self._verify_webhook_signature(data):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Signature is fake')

        user = await self._user_service.get_user_or_404(data.user_id, db)
        account, _ = await self._get_or_create_account(data.account_id, user, db)

        # Если понадобится вложенный begin (begin_nested, который SAVEPOINT) - создам отдельную функцию
        await db.rollback()
        try:
            async with db.begin(): # Выполнит COMMIT, если всё успешно, иначе ROLLBACK
                db.add(Payment(
                    transaction_id = data.transaction_id,
                    amount = data.amount,
                    account = account,
                ))
                await self._change_account_balance(account.id, data.amount, db)
                return True
        except IntegrityError:
            # будет вызвано при попытке создания дубликата т.к transaction_id должно
            # быть уникально, т.е это блок обработки повторного вызова.
            _logger.info("Attempt to apply already applied payment. Attempt ignored.")
            return False

    async def get_user_accounts(self, user: ExistsUser, db: AsyncDBSession) -> list[AccountRead]:
        return list(
            AccountRead.model_validate(acc, from_attributes=True) for acc in
            await db.scalar(select(User.accounts).where(User.id == user.id)) or []
        )

    def _assert_account_belong_to_user(self, account: Account, owner: ExistsUser):
        """
        Проверяет, что аккаунт принадлежит пользователю. В случае, если нет - поднимает HTTPException с 403 кодом.
        Raises:
            HTTPException: Аккаунт не принадлежит переданному пользователю, 403 код
        """
        if account.user_id != owner.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "It's not your account")

    async def _get_account_orm_or_404(self, external_id: int, db: AsyncDBSession) -> Account:
        return await get_or_404(
            select(Account).where(Account.external_id == external_id),
            f"Account by external_id {external_id} does not exists",
            db
        )

    async def get_account_or_404(self, external_id: int, owner: ExistsUser, db: AsyncDBSession) -> AccountRead:
        """
        Raises:
            Http404: Аккаунт не существует
            HTTPException: Аккаунт не принадлежит переданному пользователю, 403 код
        """
        account = await self._get_account_orm_or_404(external_id, db)
        self._assert_account_belong_to_user(account, owner)
        return AccountRead.model_validate(account, from_attributes=True)

    async def get_account_payments(self, external_id: int, owner: ExistsUser, db: AsyncDBSession) -> list[PaymentRead]:
        """
        Raises:
            Http404: Аккаунт не существует
            HTTPException: Аккаунт не принадлежит переданному пользователю, 403 код
        """
        account = await self._get_account_orm_or_404(external_id, db)
        self._assert_account_belong_to_user(account, owner)

        stmt = select(Payment).where(Payment.account == account)
        return list(
            PaymentRead.model_validate(p, from_attributes=True)
            for p in await db.scalars(stmt)
        )

### Deps ###
@AppScopeDependency
def get_account_service(user_service: UserService = Depends(get_user_service)) -> AccountService:
    return AccountService(
        user_service = user_service
    )
