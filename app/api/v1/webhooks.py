from typing import Literal

from fastapi import APIRouter, Depends

from app.modules.accounts import PaymentWebhookData, AccountService, get_account_service
from app.core.database    import get_db, AsyncDBSession

router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post('/payment', response_model=dict[Literal['detail'], str])
async def payment(
        data: PaymentWebhookData,
        service: AccountService = Depends(get_account_service),
        db: AsyncDBSession = Depends(get_db),
    ):

    processed = await service.try_process_payment(data, db)
    return {'detail': 'Successful processed' if processed else 'Processed already'}
