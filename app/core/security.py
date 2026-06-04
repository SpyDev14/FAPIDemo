import hashlib
from app.core.config import settings

_SECRET_KEY_BYTES: bytes = settings.SECRET_KEY.encode()

def check_password(plain_pass: str, hashed_pass: str) -> bool:
	raise NotImplementedError

def hash_password(password: str) -> str:
	raise NotADirectoryError

def encode_jwt_token(payload: dict):
	raise NotImplementedError


def check_string_signature(string: str, signature: str) -> bool:
	raise NotImplementedError
