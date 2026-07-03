import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError
from app.modules.auth import AuthService, AuthTokens, get_current_user, get_current_admin
from app.modules.users import User
from app.core.exceptions import Http404


def _get_mock_user(): return User(id=1, email="test@test.com", is_active=True, hashed_password="hashed")
class TestAuthService:
    def setup_method(self):
        self.service = AuthService(db=AsyncMock(), user_service=AsyncMock())

    async def test_login_success(self):
        mock_user = _get_mock_user()
        self.service._db.scalar = AsyncMock(return_value=mock_user)
        with patch('app.modules.auth.verify_password', return_value=True):
            with patch('app.modules.auth._create_auth_tokens', return_value=AuthTokens(access="a", refresh="r")):
                result = await self.service.login("test@test.com", "pass")
                assert result == AuthTokens(access="a", refresh="r")
                # Можно проверить, что запрос к БД был сделан (но не с какими аргументами)
                self.service._db.scalar.assert_called_once()

    async def test_login_user_not_found(self):
        self.service._db.scalar = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await self.service.login("wrong@test.com", "pass")
        assert exc.value.status_code == 401

    async def test_login_wrong_password(self):
        mock_user = _get_mock_user()
        self.service._db.scalar = AsyncMock(return_value=mock_user)
        with patch('app.modules.auth.verify_password', return_value=False):
            with pytest.raises(HTTPException) as exc:
                await self.service.login("test@test.com", "wrong")
            assert exc.value.status_code == 401

    async def test_login_inactive_user(self):
        mock_user = _get_mock_user()
        mock_user.is_active = False
        self.service._db.scalar = AsyncMock(return_value=mock_user)
        with pytest.raises(HTTPException) as exc:
            await self.service.login("test@test.com", "pass")
        assert exc.value.status_code == 401

    async def test_refresh_tokens_success(self):
        with patch('app.modules.auth.decode_jwt_token', return_value={"user_id": 1, "type": "refresh"}):
            with patch('app.modules.auth._create_auth_tokens', return_value=AuthTokens(access="a", refresh="r")):
                self.service._user_service.get_active_user_by_id_or_404 = AsyncMock(return_value=User(id=1))
                result = await self.service.refresh_tokens("some_token")
                assert result == AuthTokens(access="a", refresh="r")

    async def test_refresh_tokens_wrong_type(self):
        with patch('app.modules.auth.decode_jwt_token', return_value={"user_id": 1, "type": "access"}):
            with pytest.raises(HTTPException) as exc:
                await self.service.refresh_tokens("some_token")
            assert exc.value.status_code == 400

    async def test_refresh_tokens_expired(self):
        with patch('app.modules.auth.decode_jwt_token', side_effect=ExpiredSignatureError):
            with pytest.raises(HTTPException) as exc:
                await self.service.refresh_tokens("expired_token")
            assert exc.value.status_code == 401
            assert "expired" in str(exc.value.detail).lower()

    async def test_refresh_tokens_invalid_token(self):
        with patch('app.modules.auth.decode_jwt_token', side_effect=InvalidTokenError):
            with pytest.raises(HTTPException) as exc:
                await self.service.refresh_tokens("invalid_token")
            assert exc.value.status_code == 401

    async def test_refresh_tokens_validation_error(self):
        # Некорректный payload – проверяем, что выбрасывается 401
        with patch('app.modules.auth.decode_jwt_token', return_value={"wrong": "data"}):
            with pytest.raises(HTTPException) as exc:
                await self.service.refresh_tokens("bad_payload")
            assert exc.value.status_code == 401

    async def test_refresh_tokens_user_not_found(self):
        with patch('app.modules.auth.decode_jwt_token', return_value={"user_id": 999, "type": "refresh"}):
            self.service._user_service.get_active_user_by_id_or_404 = AsyncMock(
                side_effect=Http404("User not found")
            )
            with pytest.raises(Http404):
                await self.service.refresh_tokens("some_token")

    async def test_refresh_tokens_user_inactive(self):
        with patch('app.modules.auth.decode_jwt_token', return_value={"user_id": 1, "type": "refresh"}):
            self.service._user_service.get_active_user_by_id_or_404 = AsyncMock(
                side_effect=Http404("User is inactive")
            )
            with pytest.raises(Http404):
                await self.service.refresh_tokens("some_token")


class TestGetCurrentUserDep:
    async def test_get_current_user_success(self):
        # Успешный случай – проверяем, что возвращается пользователь
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        mock_user_service = AsyncMock()
        mock_user_service.get_active_user_by_id_or_404 = AsyncMock(return_value=User(id=1, email="test@test.com"))
        with patch('app.modules.auth.decode_jwt_token', return_value={"user_id": 1, "type": "access"}):
            user = await get_current_user(mock_credentials, mock_user_service)
            assert user.id == 1
            assert user.email == "test@test.com"
            # Проверяем, что сервис был вызван с правильным id (это важно для логики)
            mock_user_service.get_active_user_by_id_or_404.assert_called_once_with(1)

    async def test_get_current_user_expired(self):
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch('app.modules.auth.decode_jwt_token', side_effect=ExpiredSignatureError):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_credentials, AsyncMock())
            assert exc.value.status_code == 401

    async def test_get_current_user_invalid(self):
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch('app.modules.auth.decode_jwt_token', side_effect=InvalidTokenError):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_credentials, AsyncMock())
            assert exc.value.status_code == 401

    async def test_get_current_user_wrong_type(self):
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        with patch('app.modules.auth.decode_jwt_token', return_value={"user_id": 1, "type": "refresh"}):
            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_credentials, AsyncMock())
            assert exc.value.status_code == 401
            assert "access" in str(exc.value.detail)

    async def test_get_current_admin_success(self):
        user = User(id=1, role=User.Role.ADMIN)
        result = await get_current_admin(user)
        assert result == user

    async def test_get_current_admin_not_admin(self):
        user = User(id=1, role=User.Role.USER)
        with pytest.raises(HTTPException) as exc:
            await get_current_admin(user)
        assert exc.value.status_code == 403
