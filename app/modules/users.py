from typing import TYPE_CHECKING, Protocol
from enum import StrEnum

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, Enum, select
from pydantic import BaseModel, Field, EmailStr
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends, HTTPException

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.shortcuts import get_or_404
from app.utils.fastapi.deps import AppScopeDependency
from app.core.database import AsyncDBSession, Base, get_db

if TYPE_CHECKING:
    from app.modules.accounts import Account

### Models ###
class User(Base):
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
        ADMIN = 'admin'
        USER = 'user'

    # NOTE: часто ищем по почте (напр. при логине (auth))
    # (unique уже добавляет индекс (UNIQUE INDEX in sql))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255)) # TODO: Change VARCHAR size
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)

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

### Schemas & Protocols ###
class ExistsUser(Protocol):
    """Этот пользователь точно существует. По сути, обёртка над id для получения через аргументы"""
    # Создал, чтобы не указывать везде UserRead
    id: int

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)

class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=255)
    full_name: str = Field(max_length=255)
    password: str = Field(min_length=8)

### Services ###
class UserService:
    async def get_user_or_404(self, user_id: int, db: AsyncDBSession) -> UserRead:
        user = await get_or_404(
            select(User).where(User.id == user_id),
            f"User by id {user_id} does not exists",
            db
        )
        return UserRead.model_validate(user, from_attributes=True)

### Deps ###
@AppScopeDependency
def get_user_service() -> UserService:
    return UserService()

async def get_current_user() -> UserRead:
    raise NotImplementedError()

async def get_current_admin(user: UserRead = Depends(get_current_user)) -> UserRead:
    raise NotImplementedError()
