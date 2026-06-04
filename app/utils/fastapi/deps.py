from functools import cache
from typing    import Callable

# NOTE: Can grow into class in the future
# func[T, **P] equals to _T = TypeVar('_T); _P = ParamSpec('_P'); but only for this func scope
def AppScopeDependency[T, **P](func: Callable[P, T]) -> Callable[P, T]:
	"""
	Делает зависимость синглтоном (кеширует результат выполнения через functools cache).
	Возвращённый объект будет существовать всё время выполнения.
	"""
	return cache(func) # type: ignore
