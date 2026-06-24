from sqlalchemy.exc import IntegrityError
from sqlalchemy import Select

from app.core.exceptions import Http404
from app.core.database import Base, AsyncDBSession

# TODO: разобраться с непонятной ошибкой в вебхук эндпоинте
# <sys>:0: SAWarning: Object of type <Account> not in session, add operation along 'User.accounts' will not proceed (This warning originated from the Session 'autoflush' process, which was invoked automatically in response to a user-initiated operation. Consider using ``no_autoflush`` context manager if this warning happened while initializing objects.)
# <sys>:0: SAWarning: Object of type <Account> not in session, add operation along 'User.accounts' will not proceed (This warning originated from the Session 'autoflush' process, which was invoked automatically in response to a user-initiated operation. Consider using ``no_autoflush`` context manager if this warning happened while initializing objects.)

async def get_or_create[T: Base](
        select_stmt: Select[tuple[T]],
        new_instance: T,
        db: AsyncDBSession,
    ) -> tuple[T, bool]:
    """
    Get and return exists record or create and return new record. Returns `instance: T, created: bool`.

    Params:
        select_stmt: Select expression what returns one ore none (like `select(Account).where(user_id = data.user_id)`).
            Be executed as `db.scalars(select_stmt).one_or_none()`.
        new_instance: Instance what will be added if select_stmt returns none.

    Raises:
        MultipleResultsFound: select_stmt returns several records (raised by `ScalarResult.one_or_none`)

    Returns:
        (instance, created)
    """
    async def get_exists() -> T | None:
        return (await db.scalars(select_stmt)).one_or_none()

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
        if instance is None: raise Exception("I don't know what should happened for this error raising")
        return (instance, False)

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
