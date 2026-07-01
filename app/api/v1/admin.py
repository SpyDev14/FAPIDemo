from fastapi import APIRouter, Depends
from app.modules.auth import get_current_admin

router = APIRouter(
    prefix='/admin',
    dependencies=[Depends(get_current_admin)],
    tags=['admin'],
)


# GET   /api/v1/admin/users?$pagination,order_by,$filter            (req: admin)
# POST  /api/v1/admin/users                                         (req: admin)
# GET   /api/v1/admin/users/{id}                                    (req: admin)
# PATCH /api/v1/admin/users/{id}                                    (req: admin)
# GET   /api/v1/admin/users/{id}/accounts?order_by,$pagination      (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{number}                  (req: admin)
# GET   /api/v1/admin/users/{id}/accounts/{number}/payments?$filter (req: admin)

#@router.get()
