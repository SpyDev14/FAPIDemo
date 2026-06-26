# Версионирование API является хорошей практикой
# и не усложняет проект (просто 1 доп. подпапка и
# роутер). Взамен в случае роста проекта и необходимости
# изменить API это можно будет сделать безболезненно
# и не нарушая рамок проекта (просто новая папка: v2, и т.д)
# В прочем, можно и не делать этого, всё зависит от
# ожиданий от проекта. Если вероятность этого около нулевая,
# можно и не делать.

from fastapi import APIRouter

from app.utils.fastapi.routers import include_routers
from . import admin, users, webhooks

router = APIRouter(
    prefix='/v1',
)
include_routers(router, [
    admin.router,
    users.router,
    webhooks.router,
])
