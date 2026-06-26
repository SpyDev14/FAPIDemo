from typing import Iterable
from fastapi import APIRouter

# Pre-s: в рабочем проекте я бы такого не писал, разумеется.
# Но т.к. я в т.ч. в опред. степени отдыхаю разрабатывая этот проект,
# я буду попутно делится своими мыслями по типу этой.

# TODO: вместо такой функции лучше пойти в репо fastapi и кинуть PR на добавление ибо почему бы и нет.

# Не хватает this синтаксиса из C#.
# В C# можно написать нечто такое:
#   internal static class APIRouterExt
#   {                                  // ↓↓↓↓
#       public static void IncludeRouters(this APIRouter root, IEnumerable<APIRouter> routers)
#           => foreach (var router in routers) root.IncludeRouter(router);
#   }
#   (где-то в коде)
#   router.IncludeRouters([router1, router2]);
# Как-будто это метод router! Называется extension метод. При конфликтах (опред. у типа и в ext) выбирается метод типа,
# что конечно является минусом и в теории может привести к проблемам. Хотя если у встроенного метода сигнатура будет иной,
# то замены не будет, а если она та же - то и так всё работает. Проблема будет только при неоднозначных неявных преобразованиях.
# Но в любом случае лучше сразу продумывать момент на будущее.
# На этом (ext-методы), например, построено LINQ.
# Ps: LINQ - это методы обработки коллекций в функциональном стиле, такие как сортировка, фильтрация,
# преобразования и т.д. Напоминает SQL, только из методов и для обычных объектов в памяти.
# Также LINQ используется в Entity Framework (C# ORM) для запросов
# Пример:
# List<int> numbers = [2, 1, -5, ..., 0, 2];
# var res = numbers.Where(x => x % 2 == 0).Select(x => x * x).ToList() // Без ToList вернёт одноразовый lazy итератор
# (в res будет List с квадратами чётных чисел)
# Очень крутая и удобная штука.
# Добавляется, если импортировать статический класс (using пространство имён с ним)
# И в C# есть global using: "глобальный импорт" (для всех файлов проекта).
# Такого тоже не хватает.
# Ещё такими ext методами можно добавлять методы к enum-типам:
# [Flags]
# public enum Direction {
#     Right = 1,
#     Top = 2,
#     Left = 4,
#     Bottom = 8,
#     TopRight = Right | Top,
#     TopLeft = Top | Left,
#     BottomRight = Bottom | Right,
#     BottomLeft = Bottom | Left,
# }
# public static class DirectionImpl {
#     public static bool IsStraight(this Direction self) { ... } // (например Right, без Top / Bottom)
# }
# Кстати в Rust тоже можно добавить методы к уже определённому типу: через trait и impl <trait> for <type>
# trait APIRouterExt {
#     fn include_routers(&mut self, routers: IntoIterator<Item = APIRouter>);
# }
# impl APIRouterExt for APIRouter {
#     fn include_routers(&mut self, routers: IntoIterator<Item = APIRouter>) {
#         for router in routers { self.include_router(router); }
#     }
# }
# метод будет доступен при импорте трейта, также как это работает с ext методами C#

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
