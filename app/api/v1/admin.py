from fastapi import APIRouter, Depends, Path
from fastcrud import FastCRUD
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import AsyncDBSession, get_db
from app.core.exceptions import Http404
from app.core.security import hash_password
from app.modules.auth import get_current_admin
from app.modules.users import User, UserRead, UserCreate, UserUpdate
from app.modules.accounts import Account, AccountRead, Payment, PaymentRead

router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(get_current_admin)],
    tags=["admin"],
)

crud_users = FastCRUD(User)
crud_accounts = FastCRUD(Account)
crud_payments = FastCRUD(Payment)


class AdminUserRead(UserRead):
    is_active: bool
    accounts: list[AccountRead] = []


# ----- Пользователи -----

@router.get("/users")
async def get_users(db: AsyncDBSession = Depends(get_db)) -> list[AdminUserRead]:
    """Получить всех пользователей с их счетами."""
    stmt = select(User).where(User.role == User.Role.USER).options(joinedload(User.accounts))
    result = await db.execute(stmt)
    users = result.unique().scalars().all()
    return [AdminUserRead.model_validate(u, from_attributes=True) for u in users]


@router.post("/users")
async def create_user(data: UserCreate, db: AsyncDBSession = Depends(get_db)) -> UserRead:
    """Создать нового пользователя."""
    hashed = hash_password(data.password)
    user_data = data.model_dump()
    user_data["hashed_password"] = hashed
    del user_data["password"]

    user = await crud_users.create(db, object=user_data)
    await db.commit()
    return UserRead.model_validate(user, from_attributes=True)


@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncDBSession = Depends(get_db)) -> AdminUserRead:
    """Получить пользователя по ID с его счетами."""
    stmt = select(User).where(User.id == user_id).options(joinedload(User.accounts))
    result = await db.execute(stmt)
    user = result.unique().scalar_one_or_none()
    if not user:
        raise Http404(f"User {user_id} not found")
    return AdminUserRead.model_validate(user, from_attributes=True)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncDBSession = Depends(get_db),
) -> UserRead:
    """Обновить данные пользователя (full_name, is_active)."""
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise Http404(f"User {user_id} not found")

    updated = await crud_users.update(
        db, id=user_id, object=data.model_dump(exclude_unset=True)
    )
    await db.commit()
    return UserRead.model_validate(updated, from_attributes=True)


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncDBSession = Depends(get_db)) -> dict:
    """Удалить пользователя."""
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise Http404(f"User {user_id} not found")

    await crud_users.delete(db, id=user_id)
    await db.commit()
    return {"detail": "User deleted"}


# ----- Счета пользователя (по external_id) -----

@router.get("/users/{user_id}/accounts")
async def get_user_accounts(
    user_id: int,
    db: AsyncDBSession = Depends(get_db),
) -> list[AccountRead]:
    """Получить все счета указанного пользователя."""
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise Http404(f"User {user_id} not found")

    accounts = await crud_accounts.get_multi(db, user_id=user_id)
    return [AccountRead.model_validate(acc, from_attributes=True) for acc in accounts]


@router.get("/users/{user_id}/accounts/{account_external_id}")
async def get_user_account(
    user_id: int,
    account_external_id: int = Path(..., alias="account_external_id"),
    db: AsyncDBSession = Depends(get_db),
) -> AccountRead:
    """Получить конкретный счёт пользователя по его external_id."""
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise Http404(f"User {user_id} not found")

    account = await crud_accounts.get(
        db,
        user_id=user_id,
        external_id=account_external_id,
    )
    if not account:
        raise Http404(
            f"Account with external_id {account_external_id} not found for user {user_id}"
        )
    return AccountRead.model_validate(account, from_attributes=True)


# ----- Платежи счёта (по external_id) -----

@router.get("/users/{user_id}/accounts/{account_external_id}/payments")
async def get_account_payments(
    user_id: int,
    account_external_id: int = Path(..., alias="account_external_id"),
    db: AsyncDBSession = Depends(get_db),
) -> list[PaymentRead]:
    """Получить все платежи счёта по его external_id."""
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise Http404(f"User {user_id} not found")

    account = await crud_accounts.get(
        db,
        user_id=user_id,
        external_id=account_external_id,
    )
    if not account:
        raise Http404(
            f"Account with external_id {account_external_id} not found for user {user_id}"
        )

    payments = await crud_payments.get_multi(db, account_id=account.id)
    return [PaymentRead.model_validate(p, from_attributes=True) for p in payments]


@router.get("/users/{user_id}/accounts/{account_external_id}/payments/{payment_id}")
async def get_account_payment(
    user_id: int,
    account_external_id: int = Path(..., alias="account_external_id"),
    payment_id: int = Path(..., alias="payment_id"),
    db: AsyncDBSession = Depends(get_db),
) -> PaymentRead:
    """Получить конкретный платёж счёта."""
    user = await crud_users.get(db, id=user_id)
    if not user:
        raise Http404(f"User {user_id} not found")

    account = await crud_accounts.get(
        db,
        user_id=user_id,
        external_id=account_external_id,
    )
    if not account:
        raise Http404(
            f"Account with external_id {account_external_id} not found for user {user_id}"
        )

    payment = await crud_payments.get(
        db,
        id=payment_id,
        account_id=account.id,
    )
    if not payment:
        raise Http404(
            f"Payment {payment_id} not found for account {account_external_id}"
        )
    return PaymentRead.model_validate(payment, from_attributes=True)
