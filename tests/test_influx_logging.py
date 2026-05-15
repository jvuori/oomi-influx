import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from oomi_influx.config import InfluxSettings
from oomi_influx.influx import write_consumption
from oomi_influx.models import ConsumptionRecord

_SETTINGS = InfluxSettings(
    url="http://localhost:8086",
    token="tok",
    org="org",
    bucket="bucket",
    tag_value="meter",
)

_RECORDS = [
    ConsumptionRecord(
        timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        kwh=Decimal("0.100"),
    ),
    ConsumptionRecord(
        timestamp=datetime(2026, 1, 1, 0, 15, tzinfo=timezone.utc),
        kwh=Decimal("0.200"),
    ),
    ConsumptionRecord(
        timestamp=datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc),
        kwh=Decimal("0.300"),
    ),
]


def _mock_influx_client() -> MagicMock:
    mock = MagicMock()
    mock.write_api.return_value.write = MagicMock()
    return mock


def test_write_consumption_logs_first_and_last_timestamp(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch("oomi_influx.influx.InfluxDBClient", return_value=_mock_influx_client()):
        with caplog.at_level(logging.INFO, logger="oomi_influx.influx"):
            write_consumption(_RECORDS, _SETTINGS)

    first_ts = _RECORDS[0].timestamp.astimezone().strftime("%Y-%m-%dT%H:%M:%S")
    last_ts = _RECORDS[-1].timestamp.astimezone().strftime("%Y-%m-%dT%H:%M:%S")
    assert first_ts in caplog.text, "first record timestamp missing from log"
    assert last_ts in caplog.text, "last record timestamp missing from log"


def test_write_consumption_timestamp_range_uses_local_timezone(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # A single UTC record at midnight; in UTC+2 it becomes 02:00
    records = [
        ConsumptionRecord(
            timestamp=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
            kwh=Decimal("0.100"),
        ),
    ]
    monkeypatch.setenv("TZ", "Europe/Helsinki")
    time.tzset()

    with patch("oomi_influx.influx.InfluxDBClient", return_value=_mock_influx_client()):
        with caplog.at_level(logging.INFO, logger="oomi_influx.influx"):
            write_consumption(records, _SETTINGS)

    monkeypatch.delenv("TZ", raising=False)
    time.tzset()

    assert "+0300" in caplog.text, (
        f"expected Helsinki offset +0300 in timestamp range, got: {caplog.text!r}"
    )


def test_write_consumption_empty_logs_no_range(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with patch("oomi_influx.influx.InfluxDBClient", return_value=_mock_influx_client()):
        with caplog.at_level(logging.INFO, logger="oomi_influx.influx"):
            write_consumption([], _SETTINGS)

    assert "Writing 0 records" in caplog.text
