from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.modules.users import UserService, User
from app.core.exceptions import Http404
from app.core.security import hash_password


async def test_get_active_user_by_id_or_404_success(db_session: AsyncSession):
    user = User(
        email="test@example.com",
        hashed_password=hash_password("pass"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    service = UserService(db_session)
    result = await service.get_active_user_by_id_or_404(user.id)

    assert result.id == user.id
    assert result.is_active is True


async def test_get_active_user_by_id_or_404_not_found(db_session: AsyncSession):
    service = UserService(db_session)
    with pytest.raises(Http404):
        await service.get_active_user_by_id_or_404(999)


async def test_get_active_user_by_id_or_404_inactive(db_session: AsyncSession):
    user = User(
        email="inactive@example.com",
        hashed_password=hash_password("pass"),
        full_name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    service = UserService(db_session)
    with pytest.raises(Http404):
        await service.get_active_user_by_id_or_404(user.id)
