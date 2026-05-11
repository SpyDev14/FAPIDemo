from datetime import datetime
from decimal  import Decimal
from enum     import StrEnum

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import (
    BigInteger, String, Numeric, Enum, DateTime,
    ForeignKey, UniqueConstraint, func,
)

from app.utils.db.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.db.fk_on_delete         import CASCADE
from app.core.database                 import Base


class BaseModel(Base):
    __abstract__ = True

    # Just for IDE insert suggestions in subclasses
    __tablename__: str
    __table_args__: tuple | dict

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class User(BaseModel):
    __tablename__ = 'users'

    # I using strings for readability in logs and DB tools.
    # int enums (SMALLINT) would be faster, but the performance
    # gain is negligible for the expected load, and strings keep
    # the code and DB introspection cleaner.
    class Role(StrEnum):
        USER = 'user'
        ADMIN = 'admin'

    # search user by email on login (auth)
    # unique is index already (UNIQUE INDEX in sql)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255)) # TODO: Change VARCHAR size
    full_name: Mapped[str] = mapped_column(String(255))

    # I choose str enum instead bool flag because it's more
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
