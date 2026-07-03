from httpx import AsyncClient, ASGITransport
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
import pytest, pytest_asyncio

from app.modules import init_modules
from app.main import app
from app.core.database import Base, get_db


init_modules()

@pytest.fixture(scope="session")
async def db_engine():
    """Создаёт тестовую БД в контейнере и создаёт все таблицы."""
    with PostgresContainer("postgres:18") as postgres:
        url = postgres.get_connection_url("asyncpg")
        engine = create_async_engine(url, echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine
        await engine.dispose()

@pytest_asyncio.fixture(loop_scope="function")
async def db_session(db_engine: AsyncEngine):
    """
    Возвращает сессию, обёрнутую во внешнюю транзакцию.
    Все изменения, сделанные внутри теста (включая вложенные begin/commit),
    будут откатаны после завершения теста.
    """
    # Устанавливаем соединение и начинаем внешнюю транзакцию
    async with db_engine.connect() as connection:
        await connection.begin()  # <-- внешняя транзакция

        # Создаём сессию, привязанную к этому соединению
        async_session = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        async with async_session() as session:
            yield session
            # После выхода из теста откатываем внешнюю транзакцию
            await connection.rollback()

@pytest_asyncio.fixture(loop_scope="function")
async def client(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://test"
    ) as client: yield client

    app.dependency_overrides.clear()
