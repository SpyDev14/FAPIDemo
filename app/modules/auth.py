from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from pydantic import BaseModel
from jwt import InvalidTokenError, ExpiredSignatureError

from app.modules.users import ExistsUser, User, UserRead
from app.core.exceptions import Http404
from app.core.database import AsyncDBSession, get_db
from app.core.security import try_decode_jwt_token, encode_jwt_token, verify_password
from app.core.config import settings


class AuthTokens(BaseModel):
    access: str
    refresh: str

_USER_ID_KEY = 'user_id'

class TokenPayload(BaseModel):
    user_id: int

def _decode_auth_token(token: str) -> TokenPayload:
    try:
        payload = try_decode_jwt_token(token)
    except ExpiredSignatureError:
        raise HTTPException(401, 'Auth token is expired')
    except InvalidTokenError:
        payload = None

    if payload is None or 'user_id' not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid auth token')

### Services ###
class AuthService:
    def __init__(self, db: AsyncDBSession):
        self._db = db

    @staticmethod
    def _create_auth_tokens(user: ExistsUser) -> AuthTokens:
        payload = {_USER_ID_KEY: user.id}
        return AuthTokens(
            refresh=encode_jwt_token(payload, settings.JWT_REFRESH_TOKEN_LIFETIME),
            access=encode_jwt_token(payload, settings.JWT_ACCESS_TOKEN_LIFETIME),
        )

    async def login(self, email: str, password: str) -> AuthTokens:
        """
        Raises:
            Http404 - Пользователя с таким email не существует, либо пароль неверен
        """
        user = await self._db.scalar(select(User).where(User.email == email))

        # Не говорю что конкретно для безопасности
        if user is None or not verify_password(password, user.hashed_password):
            raise Http404("Wrong login or password")

        return self._create_auth_tokens(user)

    async def refresh_token(self, refresh_token: str) -> AuthTokens:
        """
        Raises:
            HTTPException - Токен истёк или не валиден, 401 код
        """
        payload, error = try_decode_jwt_token(refresh_token)

        TOKEN_IS_INVALID_MSG = 'Auth token is invalid'
        if error is not None:
            msg = (
                'Auth token is expired, refresh them by refresh token'
                if isinstance(error, jwt.ExpiredSignatureError)
                else TOKEN_IS_INVALID_MSG
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg)

        if _USER_ID_KEY not in



### Deps ###
def get_auth_service(db: AsyncDBSession = Depends(get_db)):
    return AuthService(db = db)

async def _get_current_user_orm(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
        db: AsyncDBSession = Depends(get_db)
    ) -> User:
    token = credentials.credentials
    payload = _decode_auth_token(token)
    user = await db.get(User, payload.user_id)

    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive or not exists")

    return user

async def get_current_user(user: User = Depends(_get_current_user_orm)) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)

async def get_current_admin(user: User = Depends(_get_current_user_orm)) -> UserRead:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have admin rights")
    return UserRead.model_validate(user, from_attributes=True)
