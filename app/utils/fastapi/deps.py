from functools import cache
from typing import Callable

# NOTE: Can grow into class in the future
# func[T, **P] equals to _T = TypeVar('_T); _P = ParamSpec('_P'); but only for this func scope
# NOTE: Ранее использовалось для зависимостей возвращающих state-less сервисы. Вероятно будет удалена в будущем.
def AppScopeDependency[T, **P](func: Callable[P, T]) -> Callable[P, T]:
	"""
	Делает зависимость синглтоном (кеширует результат выполнения через functools cache).
	Возвращённый объект будет существовать всё время выполнения.
	"""
	return cache(func) # type: ignore
