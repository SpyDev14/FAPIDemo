from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DEBUG: bool = False # sould be under SK 'cause SK validation depends on DEBUG value
    SECRET_KEY: str = 'SECRET_KEY'

    DB_USER: str
    DB_PASS: str
    DB_PORT: int
    DB_NAME: str

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator('SECRET_KEY')
    @classmethod
    def _validate_secret_key(cls, value: str, info: ValidationInfo):
        debug = info.data['DEBUG']
        if not debug and value in {cls.SECRET_KEY, 'SECRET_KEY'}:
            raise ValueError('SECRET_KEY should be specified in production')
        return value

settings = Settings()
