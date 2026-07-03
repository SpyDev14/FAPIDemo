from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
import uuid

from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib import PasswordHash
import jwt

from app.core.config import settings

_pwd_context = PasswordHash([Argon2Hasher()])
_SECRET_KEY = settings.SECRET_KEY

### Passwords ###
def hash_password(password: str) -> str:
    """Возвращает пароль в захешированном виде, готовом для проверки через verify_password."""
    return _pwd_context.hash(password)

def verify_password(plain_pass: str, hashed_pass: str) -> bool:
    """Проверяет соответствие переданного сырого пароля захешированному"""
    return _pwd_context.verify(plain_pass, hashed_pass)

### JWT tokens ###
# Эти функции общие для любых JWT токенов в проекте
# Всё специфичное для auth определено в modules.auth
def encode_jwt_token(payload: Mapping[str, Any], lifetime: timedelta) -> str:
    data = dict(payload) # ниже меняем словарь
    now = datetime.now(timezone.utc)
    data.update({
        'exp': now + lifetime,
        'iat': now,
        'jti': str(uuid.uuid4()),
    })
    return jwt.encode(data, _SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict[str, Any]:
    """
    Raises:
        jwt.ExpiredSignatureError: токен просрочился (является наследником `jwt.InvalidTokenError`)
        jwt.InvalidTokenError: токен невалиден
    """
    payload = jwt.decode(token, _SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    payload.pop('exp')
    payload.pop('iat')
    payload.pop('jti')
    return payload
