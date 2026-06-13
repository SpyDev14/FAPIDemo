from sqlalchemy import select
from fastapi import APIRouter, Depends

from app.modules.accounts import AccountRead
from app.modules.user     import User, UserRead, UserService, get_user_service, get_current_user
from app.core.database    import get_async_db_session, AsyncDBSession


router = APIRouter(prefix='/users', tags=['user'])

# $filter = *{attrs for filtering}
# GET   /me                                (req: user)
# GET   /me/accounts                       (req: user)
# GET   /me/accounts/{id}                  (req: user)
# GET   /me/accounts/{id}/payments?$filter (req: user)

@router.get('/me', response_model=UserRead)
async def get_me(curr_user: UserRead = Depends(get_current_user)):
    return curr_user

@router.get('/me/accounts', response_model=list[AccountRead])
async def get_my_accounts_list(
        curr_user: UserRead = Depends(get_current_user),
        service: UserService = Depends(get_user_service),
        db: AsyncDBSession = Depends(get_async_db_session)
    ):

    return list(
        AccountRead.model_validate(acc, from_attributes=True)
        for acc in await service.get_user_accounts(curr_user.id, db)
    )

@router.get('/me/accounts/{id}', response_model=AccountRead)
async def get_my_account_detail(id: int, user: UserRead = Depends(get_current_user)):
    raise NotImplementedError

@router.get('/me/accounts/{id}/payments')
async def get_my_account_payments(id: int, user: UserRead = Depends(get_current_user)):
    raise NotImplementedError
