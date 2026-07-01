from pydantic import BaseModel
from fastapi import APIRouter, Depends

from app.modules.accounts import PaymentWebhookData, AccountService, get_account_service


router = APIRouter(prefix='/webhooks', tags=['webhooks'])

class WebhookResponse(BaseModel):
    detail: str

@router.post('/payment')
async def payment(
        data: PaymentWebhookData,
        service: AccountService = Depends(get_account_service),
    ) -> WebhookResponse:

    processed = await service.try_process_payment(data)
    return WebhookResponse(detail='Successful processed' if processed else 'Processed already')
