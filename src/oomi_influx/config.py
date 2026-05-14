from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_URL = "https://www.oma.oomi.fi"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OOMI_", env_file=".env")

    gsrn: str
    customer_id: str
    username: str
    password: str
