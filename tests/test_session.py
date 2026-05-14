from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from oomi_influx.config import Settings
from oomi_influx.models import ConsumptionRecord, SessionExpiredError
from oomi_influx.session import OomiSession


@pytest.fixture()
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_BASE_URL", "https://oomi.test")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")
    return Settings()  # type: ignore[missing-argument]  # ty:ignore[missing-argument]


RECORD = ConsumptionRecord(
    timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    kwh=Decimal("0.1"),
)


def test_get_consumption_reauthenticates_on_expiry(settings: Settings) -> None:
    session = OomiSession(settings)

    with (
        patch("oomi_influx.session.form_login", return_value="SID") as mock_login,
        patch(
            "oomi_influx.session.establish_session",
            return_value=(MagicMock(), "TOKEN", "FWUID"),
        ),
        patch("oomi_influx.fetch.fetch_consumption") as mock_fetch,
    ):
        mock_fetch.side_effect = [SessionExpiredError("expired"), [RECORD]]
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)

        records = session.get_consumption(start, end)

    assert mock_login.call_count == 2  # initial + reauth
    assert records == [RECORD]


def test_get_consumption_no_reauth_needed(settings: Settings) -> None:
    session = OomiSession(settings)

    with (
        patch("oomi_influx.session.form_login", return_value="SID") as mock_login,
        patch(
            "oomi_influx.session.establish_session",
            return_value=(MagicMock(), "TOKEN", "FWUID"),
        ),
        patch("oomi_influx.fetch.fetch_consumption", return_value=[RECORD]),
    ):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        records = session.get_consumption(start, end)

    assert mock_login.call_count == 1
    assert records == [RECORD]
