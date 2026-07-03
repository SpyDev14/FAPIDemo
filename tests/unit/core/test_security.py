from app.core.security import hash_password, verify_password


class TestPasswords:
    def test_verify_correct_pass(self):
        plain_pass = "1234567890SuperPass"
        hashed_pass = hash_password(plain_pass)

        assert verify_password(plain_pass, hashed_pass) is True

    def test_verify_wrong_pass(self):
        plain_pass = "1234567890SuperPass"
        hashed_pass = hash_password(plain_pass)

        assert verify_password("IMHAZCKER", hashed_pass) is False
