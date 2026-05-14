from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OOMI_", env_file=".env")

    gsrn: str
    customer_id: str
    base_url: str = "https://www.oma.oomi.fi"
    username: str
    password: str
