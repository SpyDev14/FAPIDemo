from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy import Column


def _get_column(attr: InstrumentedAttribute) -> Column:
    col = attr.property.columns[0]
    if not isinstance(col, Column):
        # здесь был бы уместен TypeError, но он уже является частью интерфейса
        # других функция и я не хочу везде писать, что или <основная причина>,
        # ИЛИ <(вот это место)> (я вообще сомневаюсь, что эта ошибка когда-либо
        # поднимется, да и эти функции не расчитанны на работу с динамически
        # полученными атрибутами)
        raise Exception(f'attr.property.columns[0] returns not Column')
    return col

def length_of(attr: InstrumentedAttribute) -> int:
    """
    Возвращает макс. длину строковой колонки SQLAlchemy.

    Examples:
        >>> length = length_of(User.email) # 255, например

    Raises:
        TypeError: переданная колонка не является строковой
    """
    col = _get_column(attr)

    if not (length := getattr(col.type, "length", None)):
        raise TypeError(f"{attr.name} - не строковая колонка")
    return length
