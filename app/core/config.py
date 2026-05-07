from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic          import field_validator, ValidationInfo

class Settings(BaseSettings):
    DEBUG: bool = False # should be under SK because SK validation depends on DEBUG value
    SECRET_KEY: str = 'SECRET_KEY'

    ### [Database] ###
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str

    model_config = SettingsConfigDict(env_file='.env')

    @property
    def asyncpg_db_url(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'

    @field_validator('SECRET_KEY')
    @classmethod
    def _validate_secret_key(cls, value: str, info: ValidationInfo):
        debug = info.data['DEBUG']
        # cannot get access to cls.SECRET_KEY: AttributeError. It's pydantic magic
        if not debug and value == cls.model_fields[info.field_name].default:
            raise ValueError(f'{info.field_name} should be specified in production')
        return value

settings = Settings()
