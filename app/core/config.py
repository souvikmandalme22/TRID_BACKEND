from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "TRID"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "changeme"
    API_VERSION: str = "v1"

    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
