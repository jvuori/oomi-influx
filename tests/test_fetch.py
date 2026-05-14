import json
from datetime import datetime, timezone

import pytest
from pytest_httpx import HTTPXMock
import httpx

from oomi_influx.config import Settings
from oomi_influx.fetch import fetch_consumption
from oomi_influx.models import SessionExpiredError

BASE = "https://oomi.test"


@pytest.fixture()
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_BASE_URL", BASE)
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")
    return Settings()  # type: ignore[missing-argument]  # ty:ignore[missing-argument]


NDJSON_ROWS = "\n".join(
    [
        json.dumps({"p": "PT15M", "st": "2026-01-01T00:00Z", "bn01": 0.237}),
        json.dumps({"p": "PT15M", "st": "2026-01-01T00:15Z", "bn01": None}),
        json.dumps({"p": "PT15M", "st": "2026-01-01T00:30Z", "bn01": 0.100}),
    ]
)

AURA_SUCCESS = json.dumps(
    {
        "actions": [{"returnValue": {"returnValue": NDJSON_ROWS}}],
        "hasErrors": False,
    }
)


def test_fetch_consumption_happy_path(
    httpx_mock: HTTPXMock, settings: Settings
) -> None:
    httpx_mock.add_response(text=AURA_SUCCESS)
    client = httpx.Client()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)

    records = fetch_consumption(client, "TOKEN", "FWUID", settings, start, end)

    assert len(records) == 2  # null bn01 row is skipped
    assert records[0].kwh == 0.237
    assert records[0].timestamp == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert records[1].kwh == 0.100


def test_fetch_consumption_null_kwh_skipped(
    httpx_mock: HTTPXMock, settings: Settings
) -> None:
    httpx_mock.add_response(text=AURA_SUCCESS)
    client = httpx.Client()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)

    records = fetch_consumption(client, "TOKEN", "FWUID", settings, start, end)
    assert all(r.kwh is not None for r in records)


def test_fetch_consumption_session_expired_401(
    httpx_mock: HTTPXMock, settings: Settings
) -> None:
    httpx_mock.add_response(status_code=401)
    client = httpx.Client()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(SessionExpiredError):
        fetch_consumption(client, "TOKEN", "FWUID", settings, start, end)


def test_fetch_consumption_aura_error(
    httpx_mock: HTTPXMock, settings: Settings
) -> None:
    error_body = json.dumps({"actions": [], "hasErrors": True, "exceptionEvent": True})
    httpx_mock.add_response(text=error_body)
    client = httpx.Client()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(SessionExpiredError):
        fetch_consumption(client, "TOKEN", "FWUID", settings, start, end)
