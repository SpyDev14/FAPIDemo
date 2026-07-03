import pytest
from unittest.mock import AsyncMock, patch
from app.modules.users import UserService, User
from app.core.exceptions import Http404

class TestUserService:
    def setup_method(self):
        self.service = UserService(db=AsyncMock())

    async def test_get_active_user_by_id_or_404_success(self):
        mock_user = User(id=1, is_active=True)
        with patch('app.modules.users.get_by_id_or_404', return_value=mock_user) as mock_get:
            result = await self.service.get_active_user_by_id_or_404(1)
            assert result == mock_user
            mock_get.assert_called_once_with(User, 1, self.service._db)

    async def test_get_active_user_by_id_or_404_not_found(self):
        with patch('app.modules.users.get_by_id_or_404', side_effect=Http404("Not found")):
            with pytest.raises(Http404):
                await self.service.get_active_user_by_id_or_404(999)

    async def test_get_active_user_by_id_or_404_inactive(self):
        mock_user = User(id=1, is_active=False)
        with patch('app.modules.users.get_by_id_or_404', return_value=mock_user):
            with pytest.raises(Http404, match="is inactive"):
                await self.service.get_active_user_by_id_or_404(1)
