from typing import Literal
from fastapi import APIRouter, Depends
from app.modules.accounts import PaymentWebhookData, AccountService, get_account_service

router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post('/payment', response_model=dict[Literal['detail'], str])
async def payment(
        data: PaymentWebhookData,
        service: AccountService = Depends(get_account_service),
    ):

    processed = await service.try_process_payment(data)
    return {'detail': 'Successful processed' if processed else 'Processed already'}
