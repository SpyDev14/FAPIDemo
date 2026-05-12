from typing import Iterable
from fastapi import APIRouter

# Не хватает this синтаксиса из C#.
# В C# можно написать нечто такое:
#   internal static class APIRouterExt
#   {                           // ↓↓↓↓
#       public void IncludeRouters(this APIRouter root, IEnumerable<APIRouter> routers)
#           => foreach (var router in routers) root.include_router(router);
#   }
#   (где-то в коде)
#   router.IncludeRouters([router1, router2]);
# Как-будто это метод router! Называется extension метод. На этом, например,
# построено LINQ.
# Ps: LINQ - это методы обработки коллекций, такие как сортировка, фильтрация,
# преобразования и т.д. Напоминает SQL, только из методов и для обычных объектов в памяти).
# Также LINQ используется в Entity Framework (C# ORM)
# Пример: List<int> res = [1, -2, 5, ...].Where(x => x % 2 == 0).Select(x => x * x)
# (в res будет List с квадратами чётных чисел)
# Очень крутая и удобная штука.
# Добавляется, если импортировать статический класс (using пространство имён с ним)
# И в C# есть global using: "глобальный импорт" (для всех файлов проекта).
# Такого тоже не хватает.

# Я решил написать эту функцию, чтобы не писать каждый
# раз несколько строк с .include_router(...). Кто-то скажет
# "Over-Engineering" и скорее всего да, но всё же это удобно.

def include_routers(root: APIRouter, routers: Iterable[APIRouter]):
    """
    ```python
        for router in routers:
            root.include_router(router)
    ```
    """
    for router in routers:
        root.include_router(router)
