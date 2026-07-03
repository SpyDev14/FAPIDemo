from datetime import timedelta
import pytest, jwt
from app.core.security import hash_password, verify_password, encode_jwt_token, decode_jwt_token


class TestPasswords:
    def test_verify_correct_pass(self):
        plain_pass = "1234567890SuperPass"
        hashed_pass = hash_password(plain_pass)

        assert verify_password(plain_pass, hashed_pass) is True

    def test_verify_wrong_pass(self):
        plain_pass = "1234567890SuperPass"
        hashed_pass = hash_password(plain_pass)

        assert verify_password("IMHAZCKER", hashed_pass) is False


class TestJWT:
    def test_decoding_encoded(self):
        payload = {'param': 'good', 'count': 10}
        lifetime = timedelta(days=10)

        encoded = encode_jwt_token(payload, lifetime)
        decoded = decode_jwt_token(encoded)
        assert payload == decoded

    def test_decoding_expired(self):
        payload = {'param': 'good', 'count': 10}
        lifetime = timedelta(microseconds=0)

        encoded = encode_jwt_token(payload, lifetime)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_jwt_token(encoded)

    def test_decoding_invalid(self):
        with pytest.raises(jwt.InvalidTokenError):
            decode_jwt_token('wrong')
