from enum import StrEnum

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from pydantic import BaseModel, ValidationError
from jwt import InvalidTokenError, ExpiredSignatureError

from app.modules.users import ExistsUser, User, UserRead, UserService, get_user_service
from app.core.database import AsyncDBSession, get_db
from app.core.security import decode_jwt_token, encode_jwt_token, verify_password
from app.core.config import settings

### MARK: Schemas
class AuthTokens(BaseModel):
    access: str
    refresh: str

# Internal stuff
class _TokenType(StrEnum):
    REFRESH = 'refresh'
    ACCESS = 'access'

class _TokenPayload(BaseModel):
    user_id: int
    type: _TokenType

def _decode_auth_token(token: str) -> _TokenPayload:
    try:
        raw_payload = decode_jwt_token(token)
        return _TokenPayload.model_validate(raw_payload)
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Auth token is expired')
    except (InvalidTokenError, ValidationError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid auth token')

def _create_auth_tokens(user: ExistsUser) -> AuthTokens:
    refresh = _TokenPayload(user_id = user.id, type=_TokenType.REFRESH)
    access  = _TokenPayload(user_id = user.id, type=_TokenType.ACCESS)

    return AuthTokens(
        refresh=encode_jwt_token(refresh.model_dump(),settings.JWT_REFRESH_TOKEN_LIFETIME),
        access =encode_jwt_token(access.model_dump(), settings.JWT_ACCESS_TOKEN_LIFETIME),
    )

### MARK: Services
class AuthService:
    def __init__(self, db: AsyncDBSession, user_service: UserService):
        self._db = db
        self._user_service = user_service

    async def login(self, email: str, password: str) -> AuthTokens:
        """
        Raises:
            HTTPException: Неверен email, пароль или пользователь неактивен (не уточняется)
        """
        user = await self._db.scalar(select(User).where(User.email == email))

        # Не говорю что конкретно для безопасности
        if user is None or not user.is_active or not verify_password(password, user.hashed_password):
            raise HTTPException(401, "Wrong login or password, or user is inactive")

        return _create_auth_tokens(user)

    async def refresh_tokens(self, refresh_token: str) -> AuthTokens:
        """
        Raises:
            HTTPException:
                - Токен истёк или не валиден, 401 код
                - Это не Refresh токен, 400 код
                - Пользователь не найден или неактивен, 404 код
        """
        payload = _decode_auth_token(refresh_token)
        if payload.type != _TokenType.REFRESH:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Awaited refresh token, got {payload.type}")

        user = await self._user_service.get_active_user_orm_by_id_or_404(payload.user_id)
        return _create_auth_tokens(user)


### MARK: Deps
def get_auth_service(
        db: AsyncDBSession = Depends(get_db),
        user_service: UserService = Depends(get_user_service)
    ):
    return AuthService(db = db, user_service = user_service)

async def _get_current_user_orm(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
        user_service: UserService = Depends(get_user_service),
    ) -> User:
    token = credentials.credentials
    payload = _decode_auth_token(token)

    if payload.type != _TokenType.ACCESS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Awaited access auth token, got {payload.type}")

    user = await user_service.get_active_user_orm_by_id_or_404(payload.user_id)
    return user

async def get_current_user(user: User = Depends(_get_current_user_orm)) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)

async def get_current_admin(user: User = Depends(_get_current_user_orm)) -> UserRead:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have admin rights")
    return UserRead.model_validate(user, from_attributes=True)
