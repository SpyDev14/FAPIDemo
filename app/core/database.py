from typing import AsyncGenerator, TypeAlias
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession as _AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import BigInteger, UUID as SQL_UUID

from app.core.config import settings
from app.core.types import Money


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

# Я хотел добавить возможность импортировать тип сразу от сюда вместе с
# зависимостью, но просто "AsyncSession" мне показалось не слишком
# понятным, поэтому я добавил DB в название типа, хоть это и тавтология,
# немного (db: AsyncDBSession).
# TODO: Подумать над переименованием в просто AsyncSession
# NOTE: TypeAlias вместо синтаксиса type потому-что это в первую очередь
# просто имя для реимпорта AsyncSession, а не отдельный тип. Разница в том,
# что type не поддерживает проверку isinstance
# TODO: Возможно аннотацию как TypeAlias тоже стоит убрать.
# TODO: РЕшено: просто добавить as AsyncSession в импорт типа сверху и
# добавить комментарий, что это под реимпорт. Не делаю это сразу, чтобы
# сохранить изменение в git (не в общий worksave)
AsyncDBSession: TypeAlias = _AsyncSession
"""Для реимпорта под аннотации"""

async def get_db() -> AsyncGenerator[AsyncDBSession, None]:
    async with _async_session_maker() as session:
        yield session
