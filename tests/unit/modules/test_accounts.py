from unittest.mock import AsyncMock, patch
from uuid import UUID
import hashlib

from fastapi import HTTPException
import pytest

from app.modules.accounts import AccountService, PaymentWebhookData
from app.core.config import settings
from app.core.types import Money


def _get_test_payment_webhook_data(signature: str) -> PaymentWebhookData:
    return PaymentWebhookData(
        transaction_id=UUID("5eae174f-7cd0-472c-bd36-35660f00132b"),
        user_id=1,
        account_id=1,
        amount=Money('100.00'),
        signature=signature
    )

class TestAccountService:
    def setup_method(self):
        self.service = AccountService(db=AsyncMock())

    def test_compute_signature(self):
        secret = "_secret_"
        fields = {"b": 20, "a": "1"}
        sig = AccountService._compute_webhook_signature(fields, secret)
        expected = hashlib.sha256(b"120_secret_").hexdigest()
        assert sig == expected

    @patch.object(settings, 'SECRET_KEY', 'gfdmhghif38yrf9ew0jkf32')
    def test_verify_true_signature(self):
        data = _get_test_payment_webhook_data("1a8de2bb47c39c0b82816bd0dba196b4ba1a34743b4a2b5cd8b7b62623aa1515")
        assert self.service._verify_webhook_signature(data) is True

    @patch.object(settings, 'SECRET_KEY', 'gfdmhghif38yrf9ew0jkf32')
    def test_verify_fake_signature(self):
        data = _get_test_payment_webhook_data("fake")
        assert self.service._verify_webhook_signature(data) is False

    @patch.object(settings, 'SECRET_KEY', 'gfdmhghif38yrf9ew0jkf32')
    async def test_try_process_payment_raise_http_forbidden_on_fake_signature(self):
        data = _get_test_payment_webhook_data("bad")
        with pytest.raises(HTTPException) as exc_info:
            await self.service.try_process_payment(data)
        assert exc_info.value.status_code == 403
