from fastapi import APIRouter, Depends, Path
from sqlalchemy import select, update
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


class AdminUserRead(UserRead):
    role: User.Role
    is_active: bool
    accounts: list[AccountRead] = []


# ----- Пользователи -----

@router.get("/users")
async def get_users(db: AsyncDBSession = Depends(get_db)) -> list[AdminUserRead]:
    stmt = select(User).options(joinedload(User.accounts))
    result = await db.execute(stmt)
    users = result.unique().scalars().all()
    return [AdminUserRead.model_validate(u, from_attributes=True) for u in users]


@router.post("/users")
async def create_user(data: UserCreate, db: AsyncDBSession = Depends(get_db)) -> UserRead:
    hashed = hash_password(data.password)
    user_data = data.model_dump()
    user_data["hashed_password"] = hashed
    del user_data["password"]

    user = User(**user_data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserRead.model_validate(user, from_attributes=True)


@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncDBSession = Depends(get_db)) -> AdminUserRead:
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
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise Http404(f"User {user_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(user)
    return UserRead.model_validate(user, from_attributes=True)


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncDBSession = Depends(get_db)) -> dict:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise Http404(f"User {user_id} not found")

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    await db.commit()
    return {"detail": "User deactivated"}


# ----- Счета -----

@router.get("/users/{user_id}/accounts")
async def get_user_accounts(
    user_id: int,
    db: AsyncDBSession = Depends(get_db),
) -> list[AccountRead]:
    stmt_user = select(User).where(User.id == user_id)
    result_user = await db.execute(stmt_user)
    if not result_user.scalar_one_or_none():
        raise Http404(f"User {user_id} not found")

    stmt = select(Account).where(Account.user_id == user_id)
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    return [AccountRead.model_validate(acc, from_attributes=True) for acc in accounts]


@router.get("/users/{user_id}/accounts/{account_external_id}")
async def get_user_account(
    user_id: int,
    account_external_id: int = Path(..., alias="account_external_id"),
    db: AsyncDBSession = Depends(get_db),
) -> AccountRead:
    stmt_user = select(User).where(User.id == user_id)
    result_user = await db.execute(stmt_user)
    if not result_user.scalar_one_or_none():
        raise Http404(f"User {user_id} not found")

    stmt = select(Account).where(
        Account.user_id == user_id,
        Account.external_id == account_external_id
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if not account:
        raise Http404(
            f"Account with external_id {account_external_id} not found for user {user_id}"
        )
    return AccountRead.model_validate(account, from_attributes=True)


# ----- Платежи -----

@router.get("/users/{user_id}/accounts/{account_external_id}/payments")
async def get_account_payments(
    user_id: int,
    account_external_id: int = Path(..., alias="account_external_id"),
    db: AsyncDBSession = Depends(get_db),
) -> list[PaymentRead]:
    stmt_user = select(User).where(User.id == user_id)
    result_user = await db.execute(stmt_user)
    if not result_user.scalar_one_or_none():
        raise Http404(f"User {user_id} not found")

    stmt_account = select(Account).where(
        Account.user_id == user_id,
        Account.external_id == account_external_id
    )
    result_account = await db.execute(stmt_account)
    account = result_account.scalar_one_or_none()
    if not account:
        raise Http404(
            f"Account with external_id {account_external_id} not found for user {user_id}"
        )

    stmt = select(Payment).where(Payment.account_id == account.id).order_by(Payment.id.desc())
    result = await db.execute(stmt)
    payments = result.scalars().all()
    return [PaymentRead.model_validate(p, from_attributes=True) for p in payments]


@router.get("/users/{user_id}/accounts/{account_external_id}/payments/{payment_id}")
async def get_account_payment(
    user_id: int,
    account_external_id: int = Path(..., alias="account_external_id"),
    payment_id: int = Path(..., alias="payment_id"),
    db: AsyncDBSession = Depends(get_db),
) -> PaymentRead:
    stmt_user = select(User).where(User.id == user_id)
    result_user = await db.execute(stmt_user)
    if not result_user.scalar_one_or_none():
        raise Http404(f"User {user_id} not found")

    stmt_account = select(Account).where(
        Account.user_id == user_id,
        Account.external_id == account_external_id
    )
    result_account = await db.execute(stmt_account)
    account = result_account.scalar_one_or_none()
    if not account:
        raise Http404(
            f"Account with external_id {account_external_id} not found for user {user_id}"
        )

    stmt = select(Payment).where(
        Payment.id == payment_id,
        Payment.account_id == account.id
    )
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()
    if not payment:
        raise Http404(
            f"Payment {payment_id} not found for account {account_external_id}"
        )
    return PaymentRead.model_validate(payment, from_attributes=True)
