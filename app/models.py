from decimal import Decimal
from enum    import StrEnum, auto

from sqlalchemy.orm import relationship, Mapped
from sqlalchemy import (
    Integer, String, Numeric, Enum, DateTime,
    ForeignKey, UniqueConstraint, Column, func,
)

from app.utils.db.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.db.fk_on_delete         import CASCADE
from app.core.database                 import Base


class BaseModel(Base):
    __abstract__ = True

    # Just for annotations in subclasses
    __tablename__: str
    __table_args__: tuple | dict

    id = Column(Integer, primary_key = True)

class User(BaseModel):
    __tablename__ = "users"

    class Role(StrEnum):
        USER = auto()
        ADMIN = auto()

    # search user by email on login (auth)
    # unique is index already (UNIQUE INDEX in sql)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)

    # i choose str enum instead bool flag 'cause it's more
    # flexible for future extending without overengineering
    # (just string instead bool in db).
    role = Column(Enum(Role), default=Role.USER, nullable=False)

    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="user", cascade=ALL_AND_DELETE_ORPHAN
    )

    # If we also have other roles (like "Manager"), I would add
    # here properties / methods for check permissions (`can_create_users`,
    # `can_view_users`, `can_edit_user(User)`, etc.) or `has_permission`
    # and `Permission` enum (user.has_permission(Perms.CAN_VIEW_USERS))
    # If needs more diffirence roles & permissions, i will create special
    # models for it. This is not necessary now and will be overengineering.

    # I add this property for clearly check what is admin:
    # `if user.is_admin` instead of `if user.role == User.Role.ADMIN`.
    # it's more flexible for potential changes in the future, and more
    # readable.
    @property
    def is_admin(self): return self.role == User.Role.ADMIN

# i use Numeric (Decimal) 'cause float has inaccuracies in
# rounding, that absolutelly not allowed in finances (i will be detailed)
Money = Numeric(15, 2)
class Account(BaseModel):
    """`User` bank account ("Счёт")"""
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint('user_id', 'number', name='unique_user_account_number'),
    )

    # <- global unique id (from BaseModel) for local links: faster JOINs, simple work
    user_id = Column(Integer, ForeignKey(User.id, ondelete=CASCADE), index=True, nullable=False)
    number = Column(Integer, nullable=False) # number of user account. Unique for one user, not unique global.
    user: Mapped[User] = relationship(User, back_populates="accounts")
    balance = Column(Money, default=Decimal("0.00"), nullable=False)

    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="account", cascade=ALL_AND_DELETE_ORPHAN
    )

class Payment(BaseModel):
    __tablename__ = "payments"

    amount = Column(Money, nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id, ondelete=CASCADE), index=True, nullable=False)
    account: Mapped[Account] = relationship(Account, back_populates="payments")
    transaction_id = Column(String(36), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
