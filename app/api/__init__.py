from fastapi import APIRouter

from app.utils.fastapi.routers import include_routers
from . import v1

api_router = APIRouter(
    prefix='/api',
)
include_routers(api_router, [
    v1.router,
])


# USER API:
# GET   /api/v1/users/me                                (req: user)
# GET   /api/v1/users/me/accounts                       (req: user)
# GET   /api/v1/users/me/accounts/{id}                  (req: user)
# GET   /api/v1/users/me/accounts/{id}/payments?$filter (req: user)

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

# AUTH:
# POST  /api/v1/auth/login
# POST  /api/v1/auth/refresh

# WEBHOOKS:
# POST  /api/v1/webhooks/payment
