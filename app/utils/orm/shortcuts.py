from typing import Awaitable, Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy import Select

from app.core.exceptions import Http404
from app.core.database import Base, AsyncDBSession

# TODO: разобраться с непонятной ошибкой в вебхук эндпоинте
# <sys>:0: SAWarning: Object of type <Account> not in session, add operation along 'User.accounts' will not proceed (This warning originated from the Session 'autoflush' process, which was invoked automatically in response to a user-initiated operation. Consider using ``no_autoflush`` context manager if this warning happened while initializing objects.)
# <sys>:0: SAWarning: Object of type <Account> not in session, add operation along 'User.accounts' will not proceed (This warning originated from the Session 'autoflush' process, which was invoked automatically in response to a user-initiated operation. Consider using ``no_autoflush`` context manager if this warning happened while initializing objects.)

# TODO: Перевести докстринги на русский, ибо почему они вообще на английском 🤯🤯🤯
async def _get_or_create_by_getter[T: Base](
        get_exists: Callable[[], Awaitable[T | None]],
        new_instance: T,
        db: AsyncDBSession,
    ) -> tuple[T, bool]:
    instance = await get_exists()

    if instance is not None:
        return (instance, False)

    try:
        async with db.begin_nested():
            db.add(new_instance)
            await db.flush()
            return (new_instance, True)
    except IntegrityError: # Race condition insert (IntegrityError raised if some unique constraint is violated)
        # savepoint (begin_nested) is already rollback
        instance = await get_exists()
        if instance is None: raise # I don't know what should happened for this error raising, but is not an our case
        return (instance, False)

async def get_or_create[T: Base](
        stmt: Select[tuple[T]],
        new_instance: T,
        db: AsyncDBSession,
    ) -> tuple[T, bool]:
    """
    Get and return exists record or create and return new record. Returns `instance: T, created: bool`.

    Params:
        stmt: Select expression what returns one ore none (like `select(Account).where(user_id = data.user_id)`).
            Be executed as `db.scalars(stmt).one_or_none()`.
        new_instance: Instance what will be added if stmt returns none.

    Raises:
        MultipleResultsFound: stmt returns several records (raised by `ScalarResult.one_or_none`)

    Returns:
        (instance, created)
    """
    async def get_exists() -> T | None:
        return (await db.scalars(stmt)).one_or_none()
    return await _get_or_create_by_getter(get_exists, new_instance, db)

async def get_by_id_or_create[T: Base](
        model: type[T],
        id: int,
        new_instance: T,
        db: AsyncDBSession,
    ) -> tuple[T, bool]:
    """
    Get and return exists record by given id by `db.get` (use session cache) or create and return new record. Returns `instance: T, created: bool`.

    Params:
        new_instance: Instance what will be added if select_stmt returns none.

    Returns:
        (instance, created)
    """
    async def get_exists() -> T | None:
        return await db.get(model, id)
    return await _get_or_create_by_getter(get_exists, new_instance, db)


async def is_exists(stmt: Select, db: AsyncDBSession) -> bool:
    return (
        await db.execute(stmt.exists().select())
    ).scalar() is True

async def get_or_404[T: Base](stmt: Select[tuple[T]], not_found_msg: str, db: AsyncDBSession) -> T:
    """
    Return record or raise `app.core.exceptions.Http404` with given `not_found_msg`.
    Raises:
        Http404: given `stmt` returns `None`.
        MultipleResultsFound: `stmt` returns several records (raised by `ScalarResult.one_or_none`)
    """
    obj = (await db.scalars(stmt)).one_or_none()
    if obj is None:
        raise Http404(not_found_msg)
    return obj

async def get_by_id_or_404[T: Base](model: type[T], id: int, db: AsyncDBSession) -> T:
    """
    Return record by id (pk, but for all `Base` pk is `id`) by `db.get(model, id)` (with session cache)
    or raise `app.core.exceptions.Http404` with detail like "`User` by id `5` does not exists"

    Raises:
        Http404: record not exists (`db.get` returns `None`).
    """
    obj = await db.get(model, id)
    if obj is None:
        raise Http404(f"{model.__name__} by id {id} does not exists")
    return obj
