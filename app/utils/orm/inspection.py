from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy import Column


def length_of(attr: InstrumentedAttribute) -> int:
    """
    Возвращает макс. длину строковой колонки SQLAlchemy.

    Examples:
        >>> length = length_of(User.email)  # 255, например

    Raises:
        TypeError: переданная колонка не является строковой
    """
    col: Column = attr.property.columns[0]

    if not (length := getattr(col.type, "length", None)):
        raise TypeError(f"{attr.name} - не строковая колонка")
    return length
