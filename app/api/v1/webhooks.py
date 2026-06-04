from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, status, Response, Depends

from app.modules.accounts import PaymentWebhookSchema, PaymentService, get_webhook_service
from app.modules.user     import UserService, get_user_service
from app.core.database    import get_async_db_session

router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post('/payment')
async def payment(
    data: PaymentWebhookSchema,
    service: PaymentService = Depends(get_webhook_service),
    user_service: UserService = Depends(get_user_service),
    db_session: AsyncSession = Depends(get_async_db_session)):

    if not service.verify_webhook_signature(data):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Signature is fake")

    user = await user_service.get_user_or_404(data.user_id, db_session)
    processed = await service.try_apply_payment(data, user, db_session)
    return Response(
        "Successful processed" if processed else "Processed already",
        status_code=status.HTTP_200_OK
    )
