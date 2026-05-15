from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import InfluxSettings
from .models import ConsumptionRecord


def write_consumption(
    records: list[ConsumptionRecord],
    settings: InfluxSettings,
    metering_point: str,
) -> None:
    client = InfluxDBClient(
        url=settings.url,
        token=settings.token,
        org=settings.org,
    )
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        points = [
            Point("electricity_consumption")
            .tag("metering_point", metering_point)
            .field("consumption_kwh", float(record.kwh))
            .field("consumption_wh", float(record.kwh) * 1000)
            .field("resolution", "PT15MIN")
            .time(record.timestamp, WritePrecision.NS)
            for record in records
        ]
        write_api.write(bucket=settings.bucket, record=points)
    finally:
        client.close()
