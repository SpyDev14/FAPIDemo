from decimal import Decimal
from enum    import StrEnum, auto

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

    # Just for annotations in subclasses
    __tablename__: str
    __table_args__: tuple | dict

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class User(BaseModel):
    __tablename__ = "users"

    # I using strings for readability in logs and DB tools.
    # int enums (SMALLINT) would be faster, but the performance
    # gain is negligible for the expected load, and strings keep
    # the code and DB introspection cleaner.
    class Role(StrEnum):
        USER = auto()
        ADMIN = auto()

    # search user by email on login (auth)
    # unique is index already (UNIQUE INDEX in sql)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255)) # TODO: Change VARCHAR size
    full_name: Mapped[str] = mapped_column(String(127))

    # I choose str enum instead bool flag because it's more
    # flexible for future extending without over-engineering
    # (just string instead bool in db).

    # DO NOT USE DIRECTLY FOR ROLE CHECKING. Any role checks
    # should go through User instance (like `user.is_admin`
    # property) or something other for it (some new way), but
    # NOT through `.role` directly!
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER)

    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="user", cascade=ALL_AND_DELETE_ORPHAN
    )

    # I added this property for clearly check what is admin:
    # `if user.is_admin` instead of `if user.role == User.Role.ADMIN`.
    # it's more flexible for potential changes in the future, and more
    # readable.
    @property
    def is_admin(self) -> bool:
        return self.role == User.Role.ADMIN

    # If we also have other roles (like "Manager"), I would add here
    # properties / methods for check permissions (`can_create_users`,
    # `can_view_users`, `can_edit_user(User)`, etc.) or `has_permission`
    # and `Permission` enum (user.has_permission(Perms.CAN_VIEW_USERS))
    # If more differentiated roles are needed & permissions, I will create special
    # models for it. This is not necessary now and would be over-engineering.

# i use Numeric (Decimal) instead of float because float has inaccuracies in
# rounding, that absolutely not allowed in finances (i'll be detailed)
Money = Numeric(15, 2)
class Account(BaseModel):
    """`User` bank account ("Счёт")"""
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint('user_id', 'number', name='unique_user_account_number'),
    )

    # <- global unique local id (from BaseModel) for local staff: faster JOINs, simple work with it
    # For API used user_id + number (user_id, account_id, like `127, 2`)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.id, ondelete=CASCADE), index=True,
    )
    # i don't known what number type uses in other payment system, so i use BIGINT also
    # number of user account. Unique for one user, not unique at global.
    number: Mapped[int] = mapped_column(BigInteger)
    user: Mapped[User] = relationship(User, back_populates="accounts")
    balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"))

    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="account", cascade=ALL_AND_DELETE_ORPHAN,
    )

class Payment(BaseModel):
    __tablename__ = "payments"

    amount: Mapped[Decimal] = mapped_column(Money)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(Account.id, ondelete=CASCADE), index=True,
    )
    account: Mapped[Account] = relationship(Account, back_populates="payments")
    transaction_id: Mapped[str] = mapped_column(String(36), unique=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
