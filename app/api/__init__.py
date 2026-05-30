from fastapi import APIRouter
from .v1 import router as v1_router

# Я специально сделал передачу аргументов многострочной с запятой в конце,
# чтобы добавление новых параметров вызывало минимум git конфликтов
api_router = APIRouter(
    prefix='/api',
)
api_router.include_router(v1_router)

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
# GET   /api/v1/admin/users/{id}/accounts?$ordering,$pagination (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{id}                  (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{id}/payments?$filter (req: admin)

# AUTH:
# POST  /api/v1/auth/login
# POST  /api/v1/auth/refresh (req: user)

# WEBHOOKS:
# POST  /api/v1/webhooks/payment
