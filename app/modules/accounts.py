from datetime import datetime
from decimal import Decimal
from uuid import UUID
import hashlib, hmac, logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import (
    BigInteger, DateTime,
    ForeignKey, func, select, update
)
from pydantic import BaseModel
from fastapi import Depends, status, HTTPException

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.fk_on_delete import CASCADE
from app.utils.orm.shortcuts import get_by_id_or_404, get_or_404, get_or_create
from app.modules.users import ExistsUser, User
from app.core.database import Base, AsyncDBSession, get_db
from app.core.config import settings
from app.core.types import Money

_logger = logging.getLogger(__name__)

### MARK: Models
class Account(Base):
    __tablename__ = 'accounts'

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey('users.id', ondelete=CASCADE), index=True,
    )
    user: Mapped[User] = relationship(User, back_populates='accounts')
    # ID from external payment system
    external_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    # NOTE: без указания обычного default поле будет None до commit, поэтому везде нужно указывать оба
    balance: Mapped[Money] = mapped_column(server_default='0.00', default=Decimal('0.00'))

    payments: Mapped[list['Payment']] = relationship(
        'Payment', back_populates='account', cascade=ALL_AND_DELETE_ORPHAN,
    )

    def as_read(self) -> "AccountRead":
        return AccountRead.model_validate(self, from_attributes=True)

class Payment(Base):
    __tablename__ = 'payments'

    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Account.id, ondelete=CASCADE), index=True,
    )
    account: Mapped[Account] = relationship(Account, back_populates='payments')
    amount: Mapped[Money]
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

    def as_read(self) -> "PaymentRead":
        return PaymentRead.model_validate(self, from_attributes=True)


### MARK: Types
type ExistsAccount = Account | AccountRead


# TODO: переместить schemas над моделями
### MARK: Schemas
class AccountRead(BaseModel):
    external_id: int
    balance: Money

class PaymentRead(BaseModel):
    amount: Money
    created_at: datetime

class PaymentWebhookData(BaseModel):
    user_id: int
    account_id: int
    transaction_id: UUID
    amount: Money
    signature: str

### MARK: Services
class AccountService:
    def __init__(self, db: AsyncDBSession):
        self._db = db

    # TODO: Заменить аргумент data на Iterable[object], преобразовывать в Sorted[str]
    # Возможно. А возможно и оставить. Для тестов такое изменение было бы удобней т.к мы отделим
    # правила от конкретных полей, а также прибавим смысла методу _verify
    # Да, определённо нужно это сделать, так как тут мы убираем signature из data_dict, т.е завязываемся на поля data
    # для такого есть метод _verify
    @staticmethod
    def _compute_webhook_signature(fields: dict[str, object], secret_key: str):
        """
        Params:
            fields: Поля, что используются для генерации сигнатуры со значениями.
        """
        # В сторонней системе подпись генерируется как SHA256 хеш строки,
        # полученной путём конкатенации строковых представлений всех значений,
        # отсортированных в алфавитном порядке по названию и с добавленным SECRET_KEY
        # на конце. Например, для словаря user_id, account_id,
        # transaction_id и amount строка для сигнатуры будет выглядеть как:
        # f"{account_id}{amount}{transaction_id}{user_id}{secret_key}"
        signature = ''.join(str(fields[k]) for k in sorted(fields.keys())) + secret_key
        return hashlib.sha256(signature.encode()).hexdigest()

    def _verify_webhook_signature(self, data: PaymentWebhookData) -> bool:
        fields = data.model_dump(exclude={'signature'})
        expected_signature = self._compute_webhook_signature(fields, settings.SECRET_KEY)

        # ВАЖНО: hmac.compare защищён от тайминг-атак в отличии от `==`
        return hmac.compare_digest(expected_signature, data.signature)

    async def _get_or_create_account(
            self, external_id: int, user: ExistsUser
        ) -> tuple[Account, bool]:
        return await get_or_create(
            select(Account).where(Account.external_id == external_id),
            Account(user_id = user.id, external_id = external_id),
            self._db
        )

    async def _change_account_balance(self, account_id: int, amount: Money):
        """
        Изменяет баланс по переданному id на переданную сумму. Сумма (`amount`) **может быть отрицательной**.
        """
        await self._db.execute(
            update(Account)
            .where(Account.id == account_id)
            # "Все знают", но атомарное обновление чтобы из-за RC деньги не исчезали
            # Если передавать готовое новое значение из кода будет иногда перезаписывать другие обновления
            .values(balance = Account.balance + amount)
        )

    async def try_process_payment(self, data: PaymentWebhookData) -> bool:
        """
        Возвращает `True`, если было обработано и `False`, если оплата **уже** была обработана.

        **ВАЖНО:** делает COMMIT и начинает **новую** транзакцию (BEGIN).

        Raises:
            Http404: Пользователь не найден
            HTTPException: Сигнатура сфальсифицирована
        """

        if not self._verify_webhook_signature(data):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f'Signature is fake')

        user = await get_by_id_or_404(User, data.user_id, self._db)
        account, _ = await self._get_or_create_account(data.account_id, user)

        if account.user_id != user.id:
            raise HTTPException(400, f"Account by id {account.id} not belong to user by id {user.id}")

        # 1. Сохраняем потенциально созданный новый счёт
        # 2. Без commit/rollback нельзя начать новую транзакцию, что нужно ниже
        await self._db.commit()

        # Если понадобится вложенный begin (begin_nested, который SAVEPOINT) - создам отдельную функцию
        try:
            async with self._db.begin(): # Выполнит COMMIT, если всё успешно, иначе ROLLBACK
                self._db.add(Payment(
                    transaction_id = data.transaction_id,
                    amount = data.amount,
                    account = account,
                ))
                await self._change_account_balance(account.id, data.amount)
                return True
        except IntegrityError:
            # будет вызвано при попытке создания дубликата т.к transaction_id должно
            # быть уникально, т.е это блок обработки повторного вызова.
            _logger.info("Attempt to apply already applied payment. Attempt ignored.")
            return False

    async def get_user_accounts(self, user: ExistsUser) -> list[Account]:
        return list(await self._db.scalars(
            select(Account).where(Account.user_id == user.id)
        ))

    def _assert_account_belong_to_user(self, account: Account, owner: ExistsUser):
        """
        Проверяет, что аккаунт принадлежит пользователю. В случае, если нет - поднимает HTTPException с 403 кодом.

        Raises:
            HTTPException: Аккаунт не принадлежит переданному пользователю, 403 код
        """
        if account.user_id != owner.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "It is not your account")

    async def get_account_or_404(self, external_id: int, owner: ExistsUser) -> Account:
        """
        Raises:
            Http404: Аккаунта не существует
            HTTPException: Аккаунт не принадлежит переданному пользователю, 403 код
        """
        account = await get_or_404(
            select(Account).where(Account.external_id == external_id),
            f"Account by external_id {external_id} does not exists",
            self._db
        )
        self._assert_account_belong_to_user(account, owner)
        return account

    # Принимает Account а не Exists потому, что _assert проверяет значения именно на полях Account
    # TODO: Переделать под поддержку пагинации, кастомной сортировки и фильтрации
    async def get_account_payments(self, account: Account, owner: ExistsUser) -> list[Payment]:
        """
        Возвращает все payment для переданного аккаунта с сортировкой от самых новых.

        Raises:
            HTTPException: Аккаунт не принадлежит переданному пользователю, 403 код
        """
        self._assert_account_belong_to_user(account, owner)
        stmt = select(Payment).where(Payment.account_id == account.id).order_by(-Payment.id)
        return list(await self._db.scalars(stmt))

### MARK: Deps
def get_account_service(db: AsyncDBSession = Depends(get_db)) -> AccountService:
    return AccountService(db = db)
