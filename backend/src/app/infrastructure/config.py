from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"

    database_url: str
    redis_url: str

    sentry_dsn: str | None = None

    anthropic_api_key: str
    sarvam_api_key: str
    groq_api_key: str

    r2_account_id: str
    r2_access_key: str
    r2_secret_key: str
    r2_bucket: str

    meta_app_secret: str  # for webhook signature verification
    meta_phone_number_id: str | None = None
    meta_access_token: str | None = None
    meta_webhook_verify_token: str  # you choose this

settings = Settings()