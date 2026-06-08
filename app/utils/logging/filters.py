import logging
# (мне нравится смотреть на цветные логи)

# Цвета ANSI
_LEVEL_COLOR_MAP = {
    'DEBUG':    '\033[34m', # Синий
    'INFO':     '\033[36m', # Бирюзовый
    'WARNING':  '\033[33m', # Жёлтый
    'ERROR':    '\033[31m', # Красный
    'CRITICAL': '\033[35m', # Пурпурный
}
_RESET = '\033[0m'

class ColorizeLevelnameFilter(logging.Filter):
    """
    Фильтр, который оборачивает levelname в ANSI-цвета.
    """
    def filter(self, record) -> bool: # False отсеивает запись
        level = record.levelname
        color = _LEVEL_COLOR_MAP.get(level, '')
        if not color:
            return True
        record.levelname = f'{color}{level}{_RESET}'
        return True  # не отфильтровываем запись
