from typing import TYPE_CHECKING
from enum import StrEnum

from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, Enum, true, text
from pydantic import BaseModel, Field, EmailStr
from fastapi import Depends

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.inspection import length_of
from app.utils.orm.shortcuts import get_by_id_or_404
from app.core.exceptions import Http404
from app.core.database import AsyncDBSession, Base, get_db

if TYPE_CHECKING:
    from app.modules.accounts import Account

### MARK: Models
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
        """
        ВНИМАНИЕ: использование Role допускается только в ORM запросах и нигде больше.
        Для проверки прав используйте спец. методы / св-ва.
        """
        ADMIN = 'admin'
        USER = 'user'

    # NOTE: часто ищем по почте (напр. при логине (auth))
    # (unique уже добавляет индекс (UNIQUE INDEX in sql))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(128)) # С Argon2 будет 97 символов
    full_name: Mapped[str] = mapped_column(String(150))
    # используется для "мягкого" удаления пользователя
    is_active: Mapped[bool] = mapped_column(server_default=true(), default=True)

    # TODO: переписать на русский
    # I choose enum instead bool flag because it's more
    # flexible for future extending without over-engineering
    # (just string instead bool in db).

    # DO NOT USE DIRECTLY FOR ROLE CHECKING. Any role checks
    # should go through User instance (like `user.is_admin`
    # property) or something other for it (some new way), but
    # NOT through `.role` directly!
    # NOTE: без указания обычного default поле будет None до commit, поэтому везде нужно указывать оба
    role: Mapped[Role] = mapped_column(Enum(Role), server_default=text(Role.USER), default=Role.USER)

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
    # and `Permission` enum (user.has_permission(Perm.CAN_VIEW_USERS)) or
    # base class `Permission` with method check_user_has(User) ot some else.
    # If more differentiated roles are needed & permissions, i will create
    # special models for it (if needs dynamically roles). This is not
    # necessary now and will be over-engineering.

    def as_read(self) -> "UserRead":
        return UserRead.model_validate(self, from_attributes=True)


### MARK: Types
# добавил, чтобы не передавать сырой user_id там, где пользователь точно должен существовать
type ExistsUser = User | UserRead

# TODO: переместить schemas над моделями
### MARK: Schemas
class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = Field(default=None)

class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=length_of(User.email))
    full_name: str = Field(max_length=length_of(User.full_name))
    password: str = Field(min_length=8)

### MARK: Services
class UserService:
    def __init__(self, db: AsyncDBSession):
        self._db = db

    async def get_active_user_by_id_or_404(self, user_id: int) -> User:
        user = await get_by_id_or_404(User, user_id, self._db)
        if not user.is_active:
            raise Http404(f"User by id {user_id} is inactive")
        return user

### MARK: Deps
def get_user_service(db: AsyncDBSession = Depends(get_db)) -> UserService:
    return UserService(db = db)
