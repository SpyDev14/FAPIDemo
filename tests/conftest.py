from dataclasses import dataclass
import asyncio

from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from httpx import AsyncClient, ASGITransport
import pytest, pytest_asyncio

from app.modules.users import User
from app.modules import init_modules
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app


init_modules()

@pytest.fixture(scope="session")
def db_url():
    with PostgresContainer("postgres:18") as postgres:
        yield postgres.get_connection_url(driver="asyncpg")

# Создаётся под каждый тест, иначе придётся делать все тесты
# выполняемыми в одном event_loop
@pytest_asyncio.fixture
async def db_engine(db_url: str):
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine):
    """
    Возвращает сессию, обёрнутую во внешнюю транзакцию.
    Все изменения откатываются после теста.
    """
    async with db_engine.connect() as connection:
        await connection.begin()
        async_session = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        async with async_session() as session:
            yield session
            await connection.rollback()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP-клиент с переопределённой зависимостью БД."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@dataclass
class TestUsers:
    admin: User
    user: User

@pytest_asyncio.fixture
async def test_users(db_session: AsyncSession) -> TestUsers:
    """Создаёт тестового пользователя и администратора в БД."""
    admin = User(
        email="admin@test.com",
        hashed_password=hash_password("adminpass"),
        full_name="Admin Test",
        role=User.Role.ADMIN,
        is_active=True,
    )
    user = User(
        email="user@test.com",
        hashed_password=hash_password("userpass"),
        full_name="User Test",
        role=User.Role.USER,
        is_active=True,
    )
    db_session.add_all([admin, user])
    await db_session.flush()
    await db_session.refresh(admin)
    await db_session.refresh(user)

    return TestUsers(admin, user)
