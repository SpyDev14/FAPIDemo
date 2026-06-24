from datetime import datetime, timedelta, timezone
import hashlib, hmac

from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib import PasswordHash
import jwt

from app.core.config import settings

_pwd_context = PasswordHash([Argon2Hasher()])
_SECRET_KEY = settings.SECRET_KEY

### Passwords ###
def hash_password(password: str) -> str:
    return _pwd_context.hash(password)

def check_password(plain_pass: str, hashed_pass: str) -> bool:
    return _pwd_context.verify(plain_pass, hashed_pass)

### JWT tokens ###
def create_jwt_token(payload: dict[str, object], lifetime: timedelta) -> str:
    payload = payload.copy()
    expire: datetime = datetime.now(timezone.utc) + lifetime
    payload['exp'] = expire
    return jwt.encode(payload, _SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

# def create_access_token(payload: dict[str, object]) -> str:
#     return create_jwt_token(payload, settings.JWT_ACCESS_TOKEN_LIFETIME)

# def create_refresh_token(payload: dict[str, object]) -> str:
#     return create_jwt_token(payload, settings.JWT_REFRESH_TOKEN_LIFETIME)

def decode_token(token: str) -> dict[str, object]:
    """
    Raises:
        jwt.ExpiredSignatureError: токен просрочился (является наследником `jwt.InvalidTokenError`)
        jwt.InvalidTokenError: токен невалиден
    Returns:
        payload | None, error msg
    """
    return jwt.decode(token, _SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

### Signature checking ###
def check_string_signature(string: str, signature: str) -> bool:
    expected = hashlib.sha256((string + _SECRET_KEY).encode()).hexdigest()
    return hmac.compare_digest(signature, expected)
