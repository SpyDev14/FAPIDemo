from app.models import User


async def get_current_user() -> User:
    raise NotImplementedError()

async def get_current_admin(user: User = get_current_user()):
    raise NotImplementedError()
