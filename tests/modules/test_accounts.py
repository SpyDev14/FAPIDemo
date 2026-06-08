import pytest
from app.modules.accounts import PaymentService, PaymentWebhookSchema


class TestPaymentService:
    def setup_method(self) -> None:
        self.service = PaymentService()

    def test_verify_webhook_signature(self):
        SECRET_KEY = 'gfdmhghif38yrf9ew0jkf32'

        true_data = PaymentWebhookSchema(
            transaction_id = "5eae174f-7cd0-472c-bd36-35660f00132b",
            user_id = 1,
            account_id = 1,
            amount = 100,
            signature = "7b47e41efe564a062029da3367bde8844bea0fb049f894687cee5d57f2858bc8"
        )

        assert self.service._compute_webhook_signature(true_data, SECRET_KEY) == true_data.signature
