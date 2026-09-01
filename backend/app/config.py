from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    ozon_client_id: str = ""
    ozon_api_key: str = ""
    deepseek_api_key: str = ""
    database_url: str = "sqlite:///./data/ozon_admin.db"
    cors_origins: str = "http://localhost:5173"
    public_base_url: str = "http://127.0.0.1:8000"
    upload_dir: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    queue_embedded: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def upload_path(self):
        path = Path(self.upload_dir) if self.upload_dir else BASE_DIR / "data" / "uploads" / "products"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
