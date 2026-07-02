Прогнал ТЗ по существующей архитектуре (Presentation → Service, без Repository) и добавил админский CRUD поверх `FastCRUD`, сохранив принятые в проекте соглашения: `external_id` как публичный идентификатор счёта, `transaction_id` — как публичный идентификатор платежа (аналогично тому, как уже сделано в `users.py`/`accounts.py`).

Новых зависимостей не нужно — `fastcrud` уже в `pyproject.toml`.

## Дизайн-решения (коротко)

1. **FastCRUD используется внутри сервисного слоя** (`FastCRUD(Model).get_multi(...)`), а не через автогенерируемый `crud_router`. Так роутер по-прежнему не трогает БД напрямую, а бизнес-правила (хэш пароля, скрытие админов, привязка счёта к юзеру) остаются в сервисе — это соответствует вашему `README.md`.
2. `get_multi` вызывается с `schema_to_select=...Read, return_as_model=True` — SQL сразу тянет только нужные колонки (не тащим `hashed_password`), а результат уже валидированные Pydantic-схемы.
3. Админ **не может управлять другими админами** через `/admin/users/*` — такие пользователи маскируются под 404 (чтобы не палить существование чужих админ-аккаунтов).
4. Пагинация/сортировка — общие переиспользуемые Depends-классы (`PaginationParams`, `SortingParams`), сортировка через `sort_columns`/`sort_orders` (fastcrud), фильтрация — через `__ilike`/`__gte`/`__lte`.

## Новый файл: `app/utils/fastapi/pagination.py`

```python
from typing import Annotated

from fastapi import Query


class PaginationParams:
    """Общие query-параметры пагинации для $pagination в списковых эндпоинтах."""

    def __init__(
            self,
            page: Annotated[int, Query(ge=1, description="Номер страницы")] = 1,
            items_per_page: Annotated[int, Query(ge=1, le=100, description="Кол-во элементов на странице")] = 10,
        ):
        self.page = page
        self.items_per_page = items_per_page


class SortingParams:
    """
    Общие query-параметры сортировки для $ordering.

    Кол-во значений sort_orders должно совпадать с sort_columns (либо быть одним
    значением на все колонки, либо не указано вовсе - тогда по умолчанию 'asc').
    Пример: ?sort_columns=email&sort_columns=full_name&sort_orders=asc&sort_orders=desc
    """

    def __init__(
            self,
            sort_columns: Annotated[
                list[str] | None, Query(description="Поля для сортировки, в порядке приоритета")
            ] = None,
            sort_orders: Annotated[
                list[str] | None, Query(description="Направления сортировки (asc/desc)")
            ] = None,
        ):
        self.sort_columns = sort_columns
        self.sort_orders = sort_orders
```

## `app/modules/users.py` — изменения

Добавляем импорты, расширяем `UserUpdate`, добавляем CRUD-методы в `UserService`.

```python
from typing import TYPE_CHECKING
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, Enum, true, text
from pydantic import BaseModel, Field, EmailStr
from fastapi import Depends, HTTPException, status
from fastcrud import FastCRUD

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.inspection import length_of
from app.utils.orm.shortcuts import get_by_id_or_404
from app.core.security import hash_password
from app.core.exceptions import Http404
from app.core.database import AsyncDBSession, Base, get_db

if TYPE_CHECKING:
    from app.modules.accounts import Account
```

*(секции `Models` и `Types` — без изменений)*

```python
### MARK: Schemas
class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool

class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=length_of(User.email))
    full_name: str | None = Field(default=None, max_length=length_of(User.full_name))
    is_active: bool | None = Field(default=None)

class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=length_of(User.email))
    full_name: str = Field(max_length=length_of(User.full_name))
    # Максимум нужен для предотвращения DoS атак на создание пользователя (тут такого
    # эндпоинта в публичном доступе пока нет, но всё же лучше сразу указать)
    password: str = Field(min_length=8, max_length=64)


### MARK: Services
class UserService:
    def __init__(self, db: AsyncDBSession):
        self._db = db
        self._crud = FastCRUD(User)

    async def get_active_user_by_id_or_404(self, user_id: int) -> User:
        user = await get_by_id_or_404(User, user_id, self._db)
        if not user.is_active:
            raise Http404(f"User by id {user_id} is inactive")
        return user

    # MARK: Admin CRUD
    # NOTE: намеренно не даём администратору доступ к другим администраторам
    # через этот сервис - для таких пользователей возвращаем 404, чтобы не
    # палить сам факт их существования через админский API.
    async def get_user_or_404(self, user_id: int) -> User:
        """
        Raises:
            Http404: пользователь не существует или является администратором
        """
        user = await get_by_id_or_404(User, user_id, self._db)
        if user.is_admin:
            raise Http404(f"User by id {user_id} does not exists")
        return user

    async def create_user(self, data: UserCreate) -> User:
        """
        Raises:
            HTTPException: пользователь с таким email уже существует, 409 код
        """
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        self._db.add(user)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"User with email {data.email} already exists"
            )
        await self._db.refresh(user)
        return user

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        """
        Raises:
            Http404: пользователь не существует или является администратором
            HTTPException: указанный email уже занят, 409 код
        """
        user = await self.get_user_or_404(user_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"Email {data.email} already taken")
        await self._db.refresh(user)
        return user

    async def delete_user(self, user_id: int) -> None:
        """
        Raises:
            Http404: пользователь не существует или является администратором
        """
        user = await self.get_user_or_404(user_id)
        await self._db.delete(user)  # каскадно удалит счета/платежи (ondelete=CASCADE)
        await self._db.commit()

    async def get_users_paginated(
            self,
            offset: int,
            limit: int,
            sort_columns: list[str] | None = None,
            sort_orders: list[str] | None = None,
            email: str | None = None,
            full_name: str | None = None,
            is_active: bool | None = None,
        ) -> dict:
        filters: dict[str, object] = {'role': User.Role.USER}
        if email is not None:
            filters['email__ilike'] = f'%{email}%'
        if full_name is not None:
            filters['full_name__ilike'] = f'%{full_name}%'
        if is_active is not None:
            filters['is_active'] = is_active

        return await self._crud.get_multi(
            self._db,
            offset=offset,
            limit=limit,
            sort_columns=sort_columns,
            sort_orders=sort_orders,
            schema_to_select=UserRead,
            return_as_model=True,
            **filters,
        )

### MARK: Deps
def get_user_service(db: AsyncDBSession = Depends(get_db)) -> UserService:
    return UserService(db=db)
```

## `app/modules/accounts.py` — изменения

Добавляем импорты и методы в `AccountService`:

```python
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
from fastcrud import FastCRUD

from app.utils.orm.relationship_cascade import ALL_AND_DELETE_ORPHAN
from app.utils.orm.fk_on_delete import CASCADE
from app.utils.orm.shortcuts import get_by_id_or_404, get_or_404, get_or_create
from app.modules.users import ExistsUser, User
from app.core.database import Base, AsyncDBSession, get_db
from app.core.config import settings
from app.core.types import Money
```

*(модели/схемы без изменений; в `AccountService` — добавить)*

```python
class AccountService:
    def __init__(self, db: AsyncDBSession):
        self._db = db
        self._crud_account = FastCRUD(Account)
        self._crud_payment = FastCRUD(Payment)

    # ... существующие методы без изменений ...

    # MARK: Admin CRUD
    async def get_user_accounts_paginated(
            self,
            user_id: int,
            offset: int,
            limit: int,
            sort_columns: list[str] | None = None,
            sort_orders: list[str] | None = None,
        ) -> dict:
        return await self._crud_account.get_multi(
            self._db,
            offset=offset,
            limit=limit,
            sort_columns=sort_columns,
            sort_orders=sort_orders,
            schema_to_select=AccountRead,
            return_as_model=True,
            user_id=user_id,
        )

    async def get_account_by_external_id_for_user_or_404(self, external_id: int, user_id: int) -> Account:
        """
        Raises:
            Http404: счёт не существует или не принадлежит переданному пользователю
        """
        return await get_or_404(
            select(Account).where(Account.external_id == external_id, Account.user_id == user_id),
            f"Account by external_id {external_id} does not exists for user {user_id}",
            self._db,
        )

    async def get_account_payments_paginated(
            self,
            account_id: int,
            offset: int,
            limit: int,
            sort_columns: list[str] | None = None,
            sort_orders: list[str] | None = None,
            amount_gte: Decimal | None = None,
            amount_lte: Decimal | None = None,
        ) -> dict:
        filters: dict[str, object] = {}
        if amount_gte is not None:
            filters['amount__gte'] = amount_gte
        if amount_lte is not None:
            filters['amount__lte'] = amount_lte

        return await self._crud_payment.get_multi(
            self._db,
            offset=offset,
            limit=limit,
            sort_columns=sort_columns,
            sort_orders=sort_orders,
            schema_to_select=PaymentRead,
            return_as_model=True,
            account_id=account_id,
            **filters,
        )

    async def get_payment_by_transaction_id_for_account_or_404(
            self, transaction_id: UUID, account_id: int
        ) -> Payment:
        """
        Raises:
            Http404: платёж не найден на переданном счёте
        """
        return await get_or_404(
            select(Payment).where(
                Payment.transaction_id == transaction_id, Payment.account_id == account_id
            ),
            f"Payment by transaction_id {transaction_id} does not exists",
            self._db,
        )

### MARK: Deps
def get_account_service(db: AsyncDBSession = Depends(get_db)) -> AccountService:
    return AccountService(db = db)
```

## `app/api/v1/admin.py` — полностью

```python
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastcrud.paginated import compute_offset, paginated_response

from app.modules.users import UserRead, UserCreate, UserUpdate, UserService, get_user_service, get_current_admin
from app.modules.accounts import AccountRead, PaymentRead, AccountService, get_account_service
from app.utils.fastapi.pagination import PaginationParams, SortingParams

router = APIRouter(
    prefix='/admin',
    dependencies=[Depends(get_current_admin)],
    tags=['admin'],
)


### MARK: Users
# GET /admin/users?page=1&items_per_page=10&sort_columns=email&sort_orders=asc&email=foo&is_active=true
@router.get('/users')
async def get_users_list(
        pagination: PaginationParams = Depends(),
        sorting: SortingParams = Depends(),
        email: str | None = Query(default=None, description="Фильтр по email (частичное совпадение)"),
        full_name: str | None = Query(default=None, description="Фильтр по имени (частичное совпадение)"),
        is_active: bool | None = Query(default=None),
        service: UserService = Depends(get_user_service),
    ):
    crud_data = await service.get_users_paginated(
        offset=compute_offset(pagination.page, pagination.items_per_page),
        limit=pagination.items_per_page,
        sort_columns=sorting.sort_columns,
        sort_orders=sorting.sort_orders,
        email=email,
        full_name=full_name,
        is_active=is_active,
    )
    return paginated_response(crud_data, pagination.page, pagination.items_per_page)

@router.post('/users', status_code=201)
async def create_user(
        data: UserCreate,
        service: UserService = Depends(get_user_service),
    ) -> UserRead:
    user = await service.create_user(data)
    return user.as_read()

@router.get('/users/{id}')
async def get_user_detail(
        user_id: int = Path(alias='id'),
        service: UserService = Depends(get_user_service),
    ) -> UserRead:
    user = await service.get_user_or_404(user_id)
    return user.as_read()

@router.patch('/users/{id}')
async def update_user(
        data: UserUpdate,
        user_id: int = Path(alias='id'),
        service: UserService = Depends(get_user_service),
    ) -> UserRead:
    user = await service.update_user(user_id, data)
    return user.as_read()

@router.delete('/users/{id}', status_code=204)
async def delete_user(
        user_id: int = Path(alias='id'),
        service: UserService = Depends(get_user_service),
    ) -> None:
    await service.delete_user(user_id)


### MARK: User accounts
@router.get('/users/{id}/accounts')
async def get_user_accounts_list(
        user_id: int = Path(alias='id'),
        pagination: PaginationParams = Depends(),
        sorting: SortingParams = Depends(),
        user_service: UserService = Depends(get_user_service),
        account_service: AccountService = Depends(get_account_service),
    ):
    await user_service.get_user_or_404(user_id)  # 404 если пользователь не существует
    crud_data = await account_service.get_user_accounts_paginated(
        user_id=user_id,
        offset=compute_offset(pagination.page, pagination.items_per_page),
        limit=pagination.items_per_page,
        sort_columns=sorting.sort_columns,
        sort_orders=sorting.sort_orders,
    )
    return paginated_response(crud_data, pagination.page, pagination.items_per_page)

@router.get('/users/{id}/accounts/{account_id}')
async def get_user_account_detail(
        user_id: int = Path(alias='id'),
        account_external_id: int = Path(alias='account_id'),
        service: AccountService = Depends(get_account_service),
    ) -> AccountRead:
    account = await service.get_account_by_external_id_for_user_or_404(account_external_id, user_id)
    return account.as_read()


### MARK: Account payments
@router.get('/users/{id}/accounts/{account_id}/payments')
async def get_account_payments_list(
        user_id: int = Path(alias='id'),
        account_external_id: int = Path(alias='account_id'),
        pagination: PaginationParams = Depends(),
        sorting: SortingParams = Depends(),
        amount_gte: Decimal | None = Query(default=None, description="Сумма платежа от"),
        amount_lte: Decimal | None = Query(default=None, description="Сумма платежа до"),
        service: AccountService = Depends(get_account_service),
    ):
    account = await service.get_account_by_external_id_for_user_or_404(account_external_id, user_id)
    crud_data = await service.get_account_payments_paginated(
        account_id=account.id,
        offset=compute_offset(pagination.page, pagination.items_per_page),
        limit=pagination.items_per_page,
        sort_columns=sorting.sort_columns,
        sort_orders=sorting.sort_orders,
        amount_gte=amount_gte,
        amount_lte=amount_lte,
    )
    return paginated_response(crud_data, pagination.page, pagination.items_per_page)

@router.get('/users/{id}/accounts/{account_id}/payments/{transaction_id}')
async def get_account_payment_detail(
        user_id: int = Path(alias='id'),
        account_external_id: int = Path(alias='account_id'),
        transaction_id: UUID = Path(),
        service: AccountService = Depends(get_account_service),
    ) -> PaymentRead:
    account = await service.get_account_by_external_id_for_user_or_404(account_external_id, user_id)
    payment = await service.get_payment_by_transaction_id_for_account_or_404(transaction_id, account.id)
    return payment.as_read()
```

## Что стоит доделать сами (за рамками того, что вы прислали)

- **Тест-файл** `tests/unit/modules/test_accounts.py` уже сейчас не соберётся (`AccountService()` без `db`, `_compute_webhook_signature` вызывается с 2 позиционными аргументами вместо `(fields: dict, secret_key)`) — это не связано с моим изменением, поправить сигнатуру теста отдельно.
- Ошибку `SAWarning` про `Object of type <Account> not in session` (TODO в `shortcuts.py`) можно закрыть, обернув `_get_or_create_by_getter` в `async with db.no_autoflush:` перед `db.add`.
- Если понадобится swagger-документация с явным описанием `PaginatedListResponse`, можно завести общую generic-обёртку через `create_model` — сейчас типы возвращаемых списков не аннотированы явно (FastCRUD сам формирует dict), это осознанный компромисс ради простоты.

Хотите, чтобы я также прогнал этот код (эмулированно, по вниманию к деталям) и написал юнит-тесты на новые эндпоинты admin.py?
