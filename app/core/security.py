from datetime import datetime, timedelta, timezone
from typing import Mapping

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
    """Проверяет соответствие переданного чистого пароля захешированному"""
    return _pwd_context.verify(plain_pass, hashed_pass)

### JWT tokens ###
def encode_jwt_token(payload: Mapping[str, object], lifetime: timedelta) -> str:
    data = dict(payload)
    expire = datetime.now(timezone.utc) + lifetime
    data['exp'] = expire
    return jwt.encode(data, _SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

# NOTE: Можно использовать Result из библиотеки result
# Именно такая аннотация потому, что стат. анализаторы не умеют
# работать с дискриминационными типами и если сделать оба Optional,
# через union с 2мя вариантами где только 1 Optional (`(dict, None) | (None, Exception)`)
# то определение, что первое is None не даст понять анализатору, что второе наоборот НЕ None.
# Потому тут нужно проверять на успех через `error is None`, чтобы иначе error не считалась за Optional.
def try_decode_jwt_token(token: str) -> tuple[dict[str, object], None | jwt.InvalidTokenError]:
    """
    Returns:
        `(payload, None)` при успехе, иначе `({}, error)`
    """
    # Памятка:
    #     `jwt.InvalidTokenError` - общая ошибка, токен не валиден по любой из причин
    #     `jwt.ExpiredSignatureError` - наследуется от `jwt.InvalidTokenError`, datetime
    #         из `exp` указывает, что токен уже просрочился.
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload, None
    except jwt.InvalidTokenError as error:
        return {}, error
