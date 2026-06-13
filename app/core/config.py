from datetime import timedelta
from pathlib  import Path
import logging.config

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic          import field_validator, ValidationInfo

from app.utils.logging import filters


BASE_DIR = Path(__file__).resolve().parent.parent.parent
class Settings(BaseSettings):
    DEBUG: bool = False # should be under SK because SK validation depends on DEBUG value
    SECRET_KEY: str = 'SECRET_KEY'

    ### [Database] ###
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str

    ### [Auth] ###
    JWT_REFRESH_TOKEN_LIFETIME: timedelta = timedelta(days=30)
    JWT_ACCESS_TOKEN_LIFETIME:  timedelta = timedelta(minutes=15)
    JWT_ALGORITHM: str = 'HS256'

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env'
    )

    @property
    def asyncpg_db_url(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @property
    def psycopg2_db_url(self):
        return f'postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @field_validator('SECRET_KEY')
    @classmethod
    def _validate_secret_key(cls, value: str, info: ValidationInfo):
        debug = info.data['DEBUG']
        # cannot get access to cls.SECRET_KEY: AttributeError. It's pydantic magic
        if not debug and value == cls.model_fields[info.field_name].default: # type: ignore
            raise ValueError(f'{info.field_name} should be specified in production')
        return value

settings = Settings() # type: ignore

LOGGING_CONF = {
    "version": 1,
    "filters": {
        "colorize": {'()': filters.ColorizeLevelnameFilter}
    },
    "formatters": {
        "standard": { "format": "[%(levelname)s] %(asctime)s %(module)s:%(lineno)d: %(message)s" },
    },
    "handlers": {
        "console": {
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "filters": ["colorize"],
        }
    },
    "loggers": {
        "app": {
            "level": "DEBUG" if settings.DEBUG else "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
        "propagate": False,
    }
}

def setup_logging():
    """Предназначен для вызова в main, применяет конфиг логгирования"""
    logging.config.dictConfig(LOGGING_CONF)

ALEMBIC_LOGGING_CONF = {
    "version": 1,
    "filters": {
        "colorize": {'()': filters.ColorizeLevelnameFilter}
    },
    "formatters": {
        "standard": { "format": "[%(levelname)s] %(module)s: %(message)s", }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["colorize"],
        }
    },
    "loggers": {
        "alembic": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}
