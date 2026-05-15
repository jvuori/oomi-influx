from datetime import datetime, timezone
from decimal import Decimal

import pytest
from influxdb_client import InfluxDBClient

from oomi_influx.config import InfluxSettings
from oomi_influx.influx import write_consumption
from oomi_influx.models import ConsumptionRecord

pytestmark = pytest.mark.integration


def _query_points(settings: InfluxSettings) -> list[dict]:
    client = InfluxDBClient(url=settings.url, token=settings.token, org=settings.org)
    try:
        query = f'''
from(bucket: "{settings.bucket}")
  |> range(start: 0)
  |> filter(fn: (r) => r._measurement == "{settings.measurement}")
  |> filter(fn: (r) => r._field == "{settings.field_kwh}")
'''
        tables = client.query_api().query(query, org=settings.org)
        return [
            {"timestamp": record.get_time(), "kwh": record.get_value()}
            for table in tables
            for record in table.records
        ]
    finally:
        client.close()


def test_write_consumption_round_trip(influx_settings: InfluxSettings) -> None:
    records = [
        ConsumptionRecord(
            timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            kwh=Decimal("0.250"),
        ),
        ConsumptionRecord(
            timestamp=datetime(2024, 1, 1, 0, 15, tzinfo=timezone.utc),
            kwh=Decimal("0.375"),
        ),
        ConsumptionRecord(
            timestamp=datetime(2024, 1, 1, 0, 30, tzinfo=timezone.utc),
            kwh=Decimal("0.100"),
        ),
    ]

    write_consumption(records, influx_settings)

    points = _query_points(influx_settings)

    assert len(points) == len(records)
    points_by_ts = {p["timestamp"]: p["kwh"] for p in points}
    for record in records:
        assert record.timestamp in points_by_ts
        assert abs(points_by_ts[record.timestamp] - float(record.kwh)) < 1e-9


def test_write_consumption_empty(influx_settings: InfluxSettings) -> None:
    write_consumption([], influx_settings)
