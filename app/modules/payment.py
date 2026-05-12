from typing import Protocol
from pydantic import BaseModel

### Schemas ###
class ProcessExternalPaymentData(BaseModel):
    user_id: int
    account_id: int
    transaction_id: str
    amount: int
    signature: str

### Service ###
class PaymentService(Protocol):
    @staticmethod
    async def process_external_payment(data: ProcessExternalPaymentData): ...

# class - is object. This object corresponds to PaymentService protocol
# `class _payment_service` syntax equatable to `_payment_service = type(...)`
# Used as object with assigned func-objects, not as class
class _payment_service(PaymentService):
    async def process_external_payment(data: ProcessExternalPaymentData):
        raise NotImplementedError()

### Deps ###
def get_payment_service() -> PaymentService:
    return _payment_service
