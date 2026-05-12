from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.modules.user     import User


router = APIRouter(prefix='users')

# $filter = *{attrs for filtering}
# GET   /me                                (req: user)
# GET   /me/accounts                       (req: user)
# GET   /me/accounts/{id}                  (req: user)
# GET   /me/accounts/{id}/payments?$filter (req: user)

@router.get('/me')
async def get_me(user: User = Depends(get_current_user)):
    raise NotImplementedError

@router.get('/me/accounts')
async def get_my_accounts_list(user: User = Depends(get_current_user)):
    raise NotImplementedError

@router.get('/me/accounts/{id}')
async def get_my_account_detail(account_id: int, user: User = Depends(get_current_user)):
    raise NotImplementedError

@router.get('/me/accounts/{id}/payments')
async def get_my_account_payments(account_id: int, user: User = Depends(get_current_user)):
    raise NotImplementedError
