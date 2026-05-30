from datetime import datetime
from decimal  import Decimal
from enum     import StrEnum

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import (
    BigInteger, String, Numeric, Enum, DateTime,
    ForeignKey, func,
)

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.fk_on_delete         import CASCADE
from app.modules.base.models            import BaseModel


class User(BaseModel):
    __tablename__ = 'users'

    # Я использую строки вместо чисел для лучшей читаемости в логах и
    # при использовании инструментов для работы с БД в обход ORM.
    # INT enum-ы (напр. SMALLINT) для ролей были бы быстрее, но прирост
    # производительности будет не существенен при ожидаемой нагрузке,
    # при утрате читаемости (role = 1 читается в разы хуже, чем role =
    # 'admin'). Сырые значения мы можем увидеть: при чтении логов,
    # при написании сырых SQL запросов (оптимизации), при просмотре БД
    # инструментами по типу PG Admin.
    class Role(StrEnum):
        USER = 'user'
        ADMIN = 'admin'

    # NOTE: часто ищем по почте (напр. при логине (auth))
    # (unique уже добавляет индекс (UNIQUE INDEX in sql))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255)) # TODO: Change VARCHAR size
    full_name: Mapped[str] = mapped_column(String(255))

    # I choose enum instead bool flag because it's more
    # flexible for future extending without over-engineering
    # (just string instead bool in db).

    # DO NOT USE DIRECTLY FOR ROLE CHECKING. Any role checks
    # should go through User instance (like `user.is_admin`
    # property) or something other for it (some new way), but
    # NOT through `.role` directly!
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER)

    accounts: Mapped[list['Account']] = relationship(
        'Account', back_populates='user', cascade=ALL_AND_DELETE_ORPHAN
    )

    # I added this property for clearly check what is admin:
    # `if user.is_admin` instead of `if user.role == User.Role.ADMIN`.
    # it's more flexible for potential changes in the future, and more
    # readable.
    @property
    def is_admin(self) -> bool:
        return self.role == User.Role.ADMIN

    # If we also have other roles (like "Manager"), i would add here
    # properties / methods for check permissions (`can_create_users`,
    # `can_view_users`, `can_edit_user(User)`, etc.) or `has_permission`
    # and `Permission` enum (user.has_permission(Perm.CAN_VIEW_USERS))
    # If more differentiated roles are needed & permissions, i will create
    # special models for it (if needs dynamically roles). This is not
    # necessary now and will be over-engineering.

# I use Numeric (Decimal) instead of float because float has inaccuracies in
# rounding, what absolutely not allowed in finances (common knowledge, but i
# decided mention it anyway)
# I know about type_annotation_map and their abilities, but now it be over-engineering
_Money = Numeric(15, 2) # (now i chosen simple alias so that there are no duplicate)
class Account(BaseModel):
    '''`User` bank account ("Счёт")'''
    __tablename__ = 'accounts'

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.id, ondelete=CASCADE), index=True,
    )
    # ID from external payment system. Used in webhook.
    external_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    user: Mapped[User] = relationship(User, back_populates='accounts')
    balance: Mapped[Decimal] = mapped_column(_Money, default=Decimal('0.00'))

    payments: Mapped[list['Payment']] = relationship(
        'Payment', back_populates='account', cascade=ALL_AND_DELETE_ORPHAN,
    )

class Payment(BaseModel):
    __tablename__ = 'payments'

    amount: Mapped[Decimal] = mapped_column(_Money)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Account.id, ondelete=CASCADE), index=True,
    )
    account: Mapped[Account] = relationship(Account, back_populates='payments')
    transaction_id: Mapped[str] = mapped_column(String(36), unique=True)
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
