from fastapi import APIRouter

from app.utils.routers import include_routers
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
# GET   /api/v1/admin/users?$pagination,$ordering,$filter       (req: admin)
# POST  /api/v1/admin/users                                     (req: admin)
# GET   /api/v1/admin/users/{id}                                (req: admin)
# PATCH /api/v1/admin/users/{id}                                (req: admin)
# DEL   /api/v1/admin/users/{id}                                (req: admin)
# GET   /api/v1/admin/users/{id}/accounts?$ordering,$pagination (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{id}                  (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{id}/payments?$filter (req: admin)

# AUTH:
# POST  /api/v1/auth/login
# POST  /api/v1/auth/refresh (req: user)

# WEBHOOKS:
# POST  /api/v1/webhooks/payment
