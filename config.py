from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    database_url: str = Field(..., alias="DATABASE_URL")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")
    morning_reminder_hour: int = Field(default=8, alias="MORNING_REMINDER_HOUR")
    evening_reminder_hour: int = Field(default=20, alias="EVENING_REMINDER_HOUR")

    # Payment
    yookassa_shop_id: str = Field(default="", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(default="", alias="YOOKASSA_SECRET_KEY")
    admin_backend_url: str = Field(default="http://localhost:8000", alias="ADMIN_BACKEND_URL")
    internal_token: str = Field(default="change_me", alias="INTERNAL_TOKEN")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "populate_by_name": True, "extra": "ignore"}


settings = Settings()
