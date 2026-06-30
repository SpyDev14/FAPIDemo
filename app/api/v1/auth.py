from pydantic import BaseModel
from fastapi import APIRouter, Depends

from app.modules.auth import AuthTokens, AuthService, get_auth_service

router = APIRouter(prefix='/auth', tags=['auth'])


class LoginData(BaseModel):
    email: str
    password: str

@router.post('/login')
async def login(
        data: LoginData,
        auth_service: AuthService = Depends(get_auth_service),
    ) -> AuthTokens:
    return await auth_service.login(data.email, data.password)

class RefreshData(BaseModel):
    refresh_token: str

@router.post('/refresh')
async def refresh(
        data: RefreshData,
        auth_service: AuthService = Depends(get_auth_service),
    ) -> AuthTokens:
    return await auth_service.refresh_tokens(data.refresh_token)
