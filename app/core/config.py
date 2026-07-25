from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# classe de configuração para o projeto, utilizando pydantic-settings
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

    # gera a URL de conexão com o banco de dados PostgreSQL usando asyncpg
    @computed_field
    @property
    def DATABASE_URL(self) -> SecretStr:
        url = (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    )
        return SecretStr(url)


settings = Settings()