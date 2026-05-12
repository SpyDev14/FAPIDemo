from fastapi import APIRouter
from .v1 import router as v1_router

# Я специально сделал передачу аргументов многострочной с запятой в конце,
# чтобы добавление новых параметров вызывало минимум git конфликтов
api_router = APIRouter(
    prefix='/api',
)
api_router.include_router(v1_router)

# $pagination = page_size,page
# $filter = *{attrs for filtering}
# GET   /api/v1/users/me                                    (req: user)
# GET   /api/v1/users/me/accounts                           (req: user)
# GET   /api/v1/users/me/accounts/{number}                  (req: user)
# GET   /api/v1/users/me/accounts/{number}/payments?$filter (req: user)
# GET   /api/v1/admin/users?$pagination,order_by,$filter            (req: admin)
# POST  /api/v1/admin/users                                         (req: admin)
# GET   /api/v1/admin/users/{id}                                    (req: admin)
# PATCH /api/v1/admin/users/{id}                                    (req: admin)
# GET   /api/v1/admin/users/{id}/accounts?order_by,$pagination      (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{number}                  (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{number}/payments?$filter (req: admin)
# POST  /api/v1/auth/login
# POST  /api/v1/auth/refresh (req: user)
# POST  /api/v1/webhooks/payment
