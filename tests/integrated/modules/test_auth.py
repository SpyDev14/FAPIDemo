from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import pytest

from app.modules.auth import AuthService, _create_auth_tokens
from app.modules.users import User, UserService
from app.core.security import hash_password


async def test_login_success(db_session: AsyncSession):
    user = User(
        email="login@test.com",
        hashed_password=hash_password("correct"),
        full_name="Login User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    auth_service = AuthService(db=db_session, user_service=UserService(db_session))
    tokens = await auth_service.login("login@test.com", "correct")

    assert tokens.access is not None
    assert tokens.refresh is not None


async def test_login_wrong_email(db_session: AsyncSession):
    auth_service = AuthService(db=db_session, user_service=UserService(db_session))
    with pytest.raises(HTTPException) as exc:
        await auth_service.login("unknown@test.com", "pass")
    assert exc.value.status_code == 401


async def test_login_wrong_password(db_session: AsyncSession):
    user = User(
        email="pass@test.com",
        hashed_password=hash_password("correct"),
        full_name="Password User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    auth_service = AuthService(db=db_session, user_service=UserService(db_session))
    with pytest.raises(HTTPException) as exc:
        await auth_service.login("pass@test.com", "wrong")
    assert exc.value.status_code == 401


async def test_login_inactive_user(db_session: AsyncSession):
    user = User(
        email="inactive@test.com",
        hashed_password=hash_password("correct"),
        full_name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    auth_service = AuthService(db=db_session, user_service=UserService(db_session))
    with pytest.raises(HTTPException) as exc:
        await auth_service.login("inactive@test.com", "correct")
    assert exc.value.status_code == 401


async def test_refresh_tokens_success(db_session: AsyncSession):
    user = User(
        email="refresh@test.com",
        hashed_password=hash_password("pass"),
        full_name="Refresh User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    auth_service = AuthService(db=db_session, user_service=UserService(db_session))
    old_tokens = _create_auth_tokens(user)
    new_tokens = await auth_service.refresh_tokens(old_tokens.refresh)

    assert new_tokens.access is not None
    assert new_tokens.refresh is not None
    assert new_tokens.refresh != old_tokens.refresh


async def test_refresh_tokens_invalid_token(db_session: AsyncSession):
    auth_service = AuthService(db=db_session, user_service=UserService(db_session))
    with pytest.raises(HTTPException) as exc:
        await auth_service.refresh_tokens("invalid.token.here")
    assert exc.value.status_code == 401
