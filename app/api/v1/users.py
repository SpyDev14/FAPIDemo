from fastapi import APIRouter, Depends, Path

from app.modules.accounts import AccountRead, PaymentRead, AccountService, get_account_service
from app.modules.users     import UserRead, get_current_user
from app.core.database    import get_db, AsyncDBSession


router = APIRouter(
    prefix='/users',
    tags=['user'],
    dependencies=[Depends(get_current_user)]
)

# $fsp = $filter + $sort + $pagination
# GET   /me                            (req: user)
# GET   /me/accounts                   (req: user)
# GET   /me/accounts/{id}              (req: user)
# GET   /me/accounts/{id}/payments?$fp (req: user)

@router.get('/me')
async def get_me(curr_user: UserRead = Depends(get_current_user)) -> UserRead:
    return curr_user

@router.get('/me/accounts')
async def get_my_accounts_list(
        curr_user: UserRead = Depends(get_current_user),
        service: AccountService = Depends(get_account_service),
        db: AsyncDBSession = Depends(get_db),
    ) -> list[AccountRead]:
    return await service.get_user_accounts(curr_user, db)

@router.get('/me/accounts/{id}')
async def get_my_account_detail(
        account_id: int = Path(alias='id'),
        service: AccountService = Depends(get_account_service),
        curr_user: UserRead = Depends(get_current_user),
        db: AsyncDBSession = Depends(get_db),
    ) -> AccountRead:
    return await service.get_account_or_404(account_id, curr_user, db)

@router.get('/me/accounts/{id}/payments')
async def get_my_account_payments(
        account_id: int = Path(alias='id'),
        curr_user: UserRead = Depends(get_current_user),
    ) -> list[PaymentRead]:
    raise NotImplementedError
