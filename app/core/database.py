from typing import AsyncGenerator
from uuid   import UUID

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm         import Mapped, mapped_column, DeclarativeBase
from sqlalchemy             import BigInteger, UUID as SQL_UUID

from app.core.config import settings


class Base(DeclarativeBase):
    type_annotation_map = {
        UUID: SQL_UUID
    }

    # Я использую BigInt вместо Int потому, что лишние 4 байта на
    # запись (+ 4 байта на FK) не сильно увеличивают занимаемое
    # место, но это полностью исключает проблему переполнения ID,
    # что исключает ситуацию, когда вам нужно срочно мигрировать
    # весь проект на int64 с int32, как это было с телеграмм.
    # Просто хорошая практика, экономия здесь даст микроскопическое
    # преимущество, при потенциально огромных издержках на переход
    # в случае роста проекта (команда телеграмм около года в срочном
    # режиме переписывала всю свою инфраструктуру, чем также
    # сломала старые клиенты (приложения для устройств) и многие
    # телеграмм боты, которые пришлось обновлять своим разработчикам).
    # Это тоже банальная деталь, но я решил её отметить, так как
    # это важно.
    # Макс. записей при int32 - 2 миллиарда (6 лет при 1 млн вставок в день)
    # Макс. записей при int64 - 9 квинтиллионов (хватит на вечность)
    # SQL не поддерживает unsigned int. Иначе кол-во можно было бы удвоить
    # (отрицательные числа не используются для ID, по крайней мере обычно).
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

_engine = create_async_engine(
    url=settings.asyncpg_db_url,
    echo=settings.DEBUG,
)

_async_session_maker = async_sessionmaker(
    _engine, expire_on_commit=False
)

async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session_maker() as session:
        yield session
