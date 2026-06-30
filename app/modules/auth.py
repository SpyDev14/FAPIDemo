from enum import StrEnum

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from pydantic import BaseModel, ValidationError
from jwt import InvalidTokenError, ExpiredSignatureError

from app.modules.users import ExistsUser, User, UserRead
from app.core.exceptions import Http404
from app.core.database import AsyncDBSession, get_db
from app.core.security import decode_jwt_token, encode_jwt_token, verify_password
from app.core.config import settings


class AuthTokens(BaseModel):
    access: str
    refresh: str

class _TokenType(StrEnum):
    REFRESH = 'refresh'
    ACCESS = 'access'

class _TokenPayload(BaseModel):
    user: int
    type: _TokenType

def _decode_auth_token(token: str) -> _TokenPayload:
    try:
        raw_payload = decode_jwt_token(token)
        return _TokenPayload.model_validate(raw_payload)
    except ExpiredSignatureError:
        raise HTTPException(401, 'Auth token is expired')
    except (InvalidTokenError, ValidationError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid auth token')

def _create_auth_tokens(user: ExistsUser) -> AuthTokens:
    access = _TokenPayload(user = user.id, type=_TokenType.ACCESS)
    refresh = _TokenPayload(user = user.id, type=_TokenType.REFRESH)

    return AuthTokens(
        refresh=encode_jwt_token(refresh.model_dump(), settings.JWT_REFRESH_TOKEN_LIFETIME),
        access=encode_jwt_token(access.model_dump(), settings.JWT_ACCESS_TOKEN_LIFETIME),
    )

### Services ###
class AuthService:
    def __init__(self, db: AsyncDBSession):
        self._db = db

    async def login(self, email: str, password: str) -> AuthTokens:
        """
        Raises:
            Http404 - Пользователя с таким email не существует, либо пароль неверен
        """
        user = await self._db.scalar(select(User).where(User.email == email))

        # Не говорю что конкретно для безопасности
        if user is None or not verify_password(password, user.hashed_password):
            raise Http404("Wrong login or password")

        return _create_auth_tokens(user)

    async def refresh_token(self, refresh_token: str) -> AuthTokens:
        """
        Raises:
            HTTPException - Токен истёк или не валиден, 401 код
        """
        payload = _decode_auth_token(refresh_token)
        raise NotImplementedError

### Deps ###
def get_auth_service(db: AsyncDBSession = Depends(get_db)):
    return AuthService(db = db)

async def _get_current_user_orm(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
        db: AsyncDBSession = Depends(get_db)
    ) -> User:
    token = credentials.credentials
    payload = _decode_auth_token(token)

    if payload.type != _TokenType.ACCESS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Given auth token is not access')

    user = await db.get(User, payload.user)

    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive or not exists")

    return user

async def get_current_user(user: User = Depends(_get_current_user_orm)) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)

async def get_current_admin(user: User = Depends(_get_current_user_orm)) -> UserRead:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have admin rights")
    return UserRead.model_validate(user, from_attributes=True)
