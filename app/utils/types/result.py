
from typing import Literal

# TODO: Не работает
type Result[T, E: Exception] = tuple[Literal[True], T, None] | tuple[Literal[False], None, E]
"""success, value, error"""
