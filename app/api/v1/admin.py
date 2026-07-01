from fastapi import APIRouter, Depends
from app.modules.auth import get_current_admin

from app.modules.auth import get_current_user
get_current_admin = get_current_user # type: ignore
router = APIRouter(
    prefix='/admin',
    dependencies=[Depends(get_current_admin)],
    tags=['admin'],
)


# ADMIN API:
# GET   /api/v1/admin/users?$pagination,$ordering,$filter       (req: admin) | get users
# POST  /api/v1/admin/users                                     (req: admin) | create user
# GET   /api/v1/admin/users/{id}                                (req: admin) | get user
# PATCH /api/v1/admin/users/{id}                                (req: admin) | update user
# DEL   /api/v1/admin/users/{id}                                (req: admin) | delete user
# GET   /api/v1/admin/users/{id}/accounts?$ordering,$pagination (req: admin) | get user accounts
# GET   /api/v1/admin/users/{id}/accounts/{id}                  (req: admin) | get user account
# GET   /api/v1/admin/users/{id}/accounts/{id}/payments?$filter (req: admin) | get account payments
# GET   /api/v1/admin/users/{id}/accounts/{id}/payments/{id}    (req: admin) | get account payment


# ДЛЯ ОТЛАДКИ (ВРЕМЕННО)
from sqlalchemy import select
from app.modules.users import UserRead, User
from app.core.database import get_db, AsyncDBSession

@router.get('/users')
async def get_users(db: AsyncDBSession = Depends(get_db)) -> list[UserRead]:
    return list(u.as_read() for u in await db.scalars(select(User).where(User.role == User.Role.USER)))
