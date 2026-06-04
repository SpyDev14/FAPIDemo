from datetime import datetime
from decimal  import Decimal
from typing   import TYPE_CHECKING
from uuid     import UUID
import hashlib, hmac, logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc         import IntegrityError
from sqlalchemy.orm         import relationship, Mapped, mapped_column
from sqlalchemy import (
    BigInteger, Numeric, DateTime,
    ForeignKey, func, select, update
)
from pydantic import BaseModel
from fastapi  import Depends

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.fk_on_delete         import CASCADE
from app.utils.orm.shortcuts            import get_or_create, is_exists
from app.utils.fastapi.deps             import AppScopeDependency
from app.modules.user                   import User
from app.core.database                  import Base
from app.core.config                    import settings

_logger = logging.getLogger(__name__)

### Models ###
# Base.type_annotation_map be over-engineering for it
_Money = Numeric(15, 2) # (i chosen simple alias so that there are no duplicate)
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

    # Normally we'd sort these records with newest first, but since
    # the id increases with each new record, we sort by id descending
    # instead of created_at — because I don't want to create an extra
    # index (it wouldn't make sense here). So this field is used only
    # for data storage.
    # As we all know, indexes take up disk space and slow down UPDATE
    # & INSERT, but in return they speed up any operations on that field
    # (filtering, sorting, JOINs, etc.). Therefore every index must be
    # justified and necessary; any field we frequently query against
    # should be indexed.
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
class PaymentWebhookSchema(BaseModel):
    user_id: int
    account_id: int
    transaction_id: str
    amount: int
    signature: str

### Services ###
class PaymentService:
    def _compute_webhook_signature(self, data: PaymentWebhookSchema):
        # В сторонней системе подпись генерируется как SHA256 хеш строки,
        # полученной путём конкатенации строковых представлений всех значений,
        # отсортированных в алфавитном порядке по названию и с добавленным на конце
        # SECRET_KEY. Например, для словаря user_id, account_id,
        # transaction_id и amount строка для сигнатуры будет выглядеть как:
        # f"{account_id}{amount}{transaction_id}{user_id}{secret_key}"
        data_dict = data.model_dump(exclude={'signature'})
        signature_string = ''.join(data_dict[k] for k in sorted(data_dict.keys())) + settings.SECRET_KEY
        return hashlib.sha256(signature_string.encode()).hexdigest()

    def verify_webhook_signature(self, data: PaymentWebhookSchema) -> bool:
        """Returns signature is verified"""
        expected_signature = self._compute_webhook_signature(data)

        # NOTE: use hmac.compare instead `==` because it's enforced from timing attack
        return hmac.compare_digest(expected_signature, data.signature)

    async def _get_or_create_user_account(self, external_id: int, user: 'User', db_session: AsyncSession) -> tuple[Account, bool]:
        return await get_or_create(
            select(Account).where(Account.user == user),
            Account(user = user, external_id = external_id),
            db_session
        )

    async def _change_account_balance(self, account_id: int, amount: int, db_session: AsyncSession):
        await db_session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(balance = Account.balance + amount)
        )

    async def try_apply_payment(self, data: PaymentWebhookSchema, user: 'User', db_session: AsyncSession) -> bool:
        """
        Returns `True` if processed, return `False` if already processed.
        Raises:
            HTTPException: User not found
        """
        assert data.user_id != user.id, 'Given user.id != given data.user_id'

        account, _ = await self._get_or_create_user_account(data.account_id, user, db_session)
        try:
            async with db_session.begin_nested():
                db_session.add(Payment(
                    transaction_id = data.transaction_id,
                    amount = data.amount,
                    account = account,
                ))
                await self._change_account_balance(account.id, data.amount, db_session)
                return True
        except IntegrityError: # be raised on duplicates because transaction_id is unique
            _logger.info("Attempt to apply already applied payment. Attempt ignored.")
            return False

### Deps ###
@AppScopeDependency
def get_webhook_service() -> PaymentService:
    return PaymentService()
