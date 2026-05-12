from fastapi import APIRouter

router = APIRouter(prefix='users')

# $filter = *{attrs for filtering}
# GET   /me                                    (req: user)
# GET   /me/accounts                           (req: user)
# GET   /me/accounts/{number}                  (req: user)
# GET   /me/accounts/{number}/payments?$filter (req: user)
