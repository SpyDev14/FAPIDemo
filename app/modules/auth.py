from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from jwt import InvalidTokenError, ExpiredSignatureError

from app.utils.fastapi.deps import AppScopeDependency
from app.modules.users import User, UserRead
from app.core.database import AsyncDBSession, get_db
from app.core.security import decode_token


class AuthTokens(BaseModel):
    access: str
    refresh: str

### Services ###
class AuthService:
    def login(self, email: str, password: str) -> AuthTokens:
        raise NotImplementedError

    def refresh_token(self, refresh_token: str) -> AuthTokens:
        raise NotImplementedError

### Deps ###
@AppScopeDependency
def get_auth_service():
    return AuthService()

async def _get_current_user_orm(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
        db: AsyncDBSession = Depends(get_db)
    ) -> User:
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise HTTPException(401, 'Auth token is expired')
    except InvalidTokenError:
        payload = None

    if payload is None or 'user_id' not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid auth token')

    user = await db.get(User, payload['user_id'])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive or not exists")

    return user

async def get_current_user(user: User = Depends(_get_current_user_orm)) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)

async def get_current_admin(user: User = Depends(_get_current_user_orm)) -> UserRead:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have admin rights")
    return UserRead.model_validate(user, from_attributes=True)
