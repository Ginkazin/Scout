from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

# Configurações da aplicação, carregadas a partir do arquivo .env
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str
    app_version: str

    DB_HOST: str
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str

    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @computed_field
    @property
    def DATABASE_URL(self) -> SecretStr:
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME
        )
        return SecretStr(url.render_as_string(hide_password=False))

settings = Settings()

class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DB_TEST_HOST: str
    DB_TEST_PORT: int = 5432
    DB_TEST_USER: str
    DB_TEST_PASSWORD: SecretStr
    DB_TEST_NAME: str
    


    @computed_field
    @property
    def DATABASE_URL_TEST(self) -> SecretStr:
        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_TEST_USER,
            password=self.DB_TEST_PASSWORD.get_secret_value(),
            host=self.DB_TEST_HOST,
            port=self.DB_TEST_PORT,
            database=self.DB_TEST_NAME
        )
        return SecretStr(url.render_as_string(hide_password=False))
  