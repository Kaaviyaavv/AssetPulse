from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://assetpulse:assetpulse_pw@localhost:5432/assetpulse"
    gemini_api_key: str = ""
    groq_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
