from dataclasses import dataclass, astuple

from fastapi import Depends, Request

from app.utils.fastapi.deps import AppScopeDependency
from app.modules.user import User


AccessToken = str
RefreshToken = str

@dataclass
class Tokens:
    access_token: AccessToken
    refresh_token: RefreshToken
    def __iter__(self): return iter(astuple(self))

### Services ###
class AuthService:
    def login(self, email: str, password: str) -> Tokens:
        raise NotImplementedError

    def refresh_token(self, refresh_token: RefreshToken) -> Tokens:
        raise NotImplementedError

### Deps ###
@AppScopeDependency
def get_auth_service():
    return AuthService()

def get_current_user(request: Request) -> User:
    raise NotImplementedError()

def get_current_admin(user: User = Depends(get_current_user)):
    raise NotImplementedError()
