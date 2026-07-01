from decimal import Decimal
from pydantic import GetJsonSchemaHandler
from pydantic_core import core_schema
from sqlalchemy import Numeric

# Ранее для Money использовалась локальная _Money = Numeric(...)
# в app.modules.accounts (без указания в type_annotation_map), но
# для добавления валидации и в pydantic пришлось добавлять целый
# отдельный тип.
class Money(Decimal):
    """Тип для денег. Используйте его вместо простого decimal в Pydantic & SQLAlchemy"""

    _PRECISION = 15
    _SCALE = 2

    SQLALCHEMY_TYPE = Numeric(_PRECISION, _SCALE)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler) -> core_schema.CoreSchema:
        return core_schema.decimal_schema(
            max_digits=cls._PRECISION,
            decimal_places=cls._SCALE,
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler: GetJsonSchemaHandler):
        # Получаем стандартную JSON схему (type: string, format: decimal)
        json_schema = handler(core_schema)
        # Дополняем её для документации
        digits_before = cls._PRECISION - cls._SCALE
        json_schema.update(
            {
                # Регулярка: максимум 13 цифр до точки (15-2) и 2 после
                "pattern": rf"^\d{{1,{digits_before}}}\.\d{{{cls._SCALE}}}$",
                # Красивый пример для Swagger
                "example": "1234567890123.45",
                # Подсказка для UI
                "maxLength": cls._PRECISION + 1, # длина строки; + 1 символ точки
                "minLength": cls._SCALE + 2, # как минимум: десятичная часть + точка + 0 ("0.00" при scale=2)
            }
        )
        return json_schema
