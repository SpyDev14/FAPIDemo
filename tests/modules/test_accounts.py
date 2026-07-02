from unittest.mock import MagicMock
from app.modules.accounts import AccountService


def test_webhook_signature_creating():
    SECRET_KEY = 'gfdmhghif38yrf9ew0jkf32'

    signature = "7b47e41efe564a062029da3367bde8844bea0fb049f894687cee5d57f2858bc8"
    data = dict(
        transaction_id = "5eae174f-7cd0-472c-bd36-35660f00132b",
        user_id = 1,
        account_id = 1,
        amount = 100,
        signature = signature
    )

    assert AccountService._compute_webhook_signature(data, SECRET_KEY) == signature
