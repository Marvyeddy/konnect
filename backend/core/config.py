from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parents[1] / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    TEST_DB_URL: str
    JWT_KEY: str
    JWT_ALG: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )


config = Settings()
