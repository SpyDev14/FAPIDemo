from fastapi import APIRouter

from app.api.dependencies import get_current_user
from app.modules.user     import User


router = APIRouter(prefix='users')

# $filter = *{attrs for filtering}
# GET   /me                                    (req: user)
# GET   /me/accounts                           (req: user)
# GET   /me/accounts/{number}                  (req: user)
# GET   /me/accounts/{number}/payments?$filter (req: user)

@router.get('/me')
async def get_me(user: User = ): ...
