from fastapi import APIRouter, Depends

from app.modules.user import User, get_current_user, UserDetailSchema


router = APIRouter(prefix='/users', tags=['user'])

# $filter = *{attrs for filtering}
# GET   /me                                (req: user)
# GET   /me/accounts                       (req: user)
# GET   /me/accounts/{id}                  (req: user)
# GET   /me/accounts/{id}/payments?$filter (req: user)

@router.get('/me')
async def get_me(user: User = Depends(get_current_user)):
    return UserDetailSchema.from_user(user)

@router.get('/me/accounts')
async def get_my_accounts_list(user: User = Depends(get_current_user)):
    raise NotImplementedError

@router.get('/me/accounts/{id}')
async def get_my_account_detail(account_id: int, user: User = Depends(get_current_user)):
    raise NotImplementedError

@router.get('/me/accounts/{id}/payments')
async def get_my_account_payments(account_id: int, user: User = Depends(get_current_user)):
    raise NotImplementedError
