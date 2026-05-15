from pydantic import computed_field
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def metering_point(self) -> str:
        return self.gsrn[-8:-1]


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
