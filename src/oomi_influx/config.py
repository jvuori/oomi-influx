from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_URL = "https://www.oma.oomi.fi"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OOMI_",
        env_file=".env",
        dotenv_filtering="match_prefix",
    )

    gsrn: str
    customer_id: str
    username: str
    password: str


class InfluxSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INFLUX_",
        env_file=".env",
        dotenv_filtering="match_prefix",
    )

    url: str
    token: str
    org: str
    bucket: str
    measurement: str = "electricity_consumption"
    tag_key: str = "metering_point"
    tag_value: str
    field_kwh: str = "consumption_kwh"
    field_wh: str = "consumption_wh"
    field_resolution: str = "resolution"
