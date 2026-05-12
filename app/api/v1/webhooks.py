from fastapi import APIRouter, status, Response, Depends
from app.modules.payment import ProcessExternalPaymentData, PaymentService, get_payment_service


router = APIRouter(prefix='/webhooks', tags=['webhooks'])

@router.post('/some-payment')
async def payment_route(
    data: ProcessExternalPaymentData,
    service: PaymentService = Depends(get_payment_service)):
    ...
    return Response(status_code=status.HTTP_200_OK)
