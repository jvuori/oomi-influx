from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import InfluxSettings
from .models import ConsumptionRecord


def write_consumption(
    records: list[ConsumptionRecord],
    settings: InfluxSettings,
) -> None:
    client = InfluxDBClient(
        url=settings.url,
        token=settings.token,
        org=settings.org,
    )
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        points = [
            Point(settings.measurement)
            .tag(settings.tag_key, settings.tag_value)
            .field(settings.field_kwh, float(record.kwh))
            .field(settings.field_wh, float(record.kwh) * 1000)
            .field(settings.field_resolution, "PT15MIN")
            .time(record.timestamp, WritePrecision.NS)
            for record in records
        ]
        write_api.write(bucket=settings.bucket, record=points)
    finally:
        client.close()
