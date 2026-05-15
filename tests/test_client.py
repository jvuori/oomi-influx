from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from oomi_influx.client import (
    AuraTokenNotFound,
    FwuidNotFound,
    LoginError,
    OomiClient,
    establish_session,
    form_login,
)
from oomi_influx.config import Settings
from oomi_influx.models import ConsumptionRecord

BASE = "https://www.oma.oomi.fi"

HOME_HTML_WITH_ERIC = """
<html><head>
<script src="/s/sfsites/auraFW/javascript/TESTFWUID123/aura_prod.js"></script>
</head><body></body></html>"""

HOME_HTML_NO_ERIC = "<html><body>no ERIC cookie set</body></html>"
HOME_HTML_NO_FWUID = "<html><head></head><body>no aura_prod.js script tag</body></html>"


def test_form_login_success(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/login",
        status_code=302,
        headers={"location": f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/"},
    )
    assert form_login("user@example.com", "pw") == "SESSION123"


def test_form_login_bad_credentials(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/login",
        status_code=200,
        text="Please enter your username.",
    )
    with pytest.raises(LoginError, match="Login failed"):
        form_login("user@example.com", "wrong")


def test_establish_session_extracts_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/",
        status_code=302,
        headers={
            "location": f"{BASE}/s/",
            "set-cookie": "__Host-ERIC_PROD123=eyJhbGc.eyJleHA.SIG; Path=/; Secure",
        },
    )
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_WITH_ERIC)
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_WITH_ERIC)
    client, token, fwuid = establish_session("SESSION123")
    assert token == "eyJhbGc.eyJleHA.SIG"
    assert fwuid == "TESTFWUID123"
    assert isinstance(client, httpx.Client)


def test_establish_session_no_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/",
        status_code=302,
        headers={"location": f"{BASE}/s/"},
    )
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_ERIC)
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_ERIC)
    with pytest.raises(AuraTokenNotFound):
        establish_session("SESSION123")


def test_establish_session_no_fwuid(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE}/secur/frontdoor.jsp?sid=SESSION123&retURL=/s/",
        status_code=302,
        headers={
            "location": f"{BASE}/s/",
            "set-cookie": "__Host-ERIC_PROD123=eyJhbGc.eyJleHA.SIG; Path=/; Secure",
        },
    )
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_FWUID)
    httpx_mock.add_response(url=f"{BASE}/s/", text=HOME_HTML_NO_FWUID)
    with pytest.raises(FwuidNotFound):
        establish_session("SESSION123")


@pytest.fixture()
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")
    return Settings()  # ty:ignore[missing-argument]


RECORD = ConsumptionRecord(
    timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    kwh=Decimal("0.1"),
)


def test_get_consumption_reauthenticates_on_expiry(settings: Settings) -> None:
    oomi = OomiClient(settings)

    with (
        patch("oomi_influx.client.form_login", return_value="SID") as mock_login,
        patch(
            "oomi_influx.client.establish_session",
            return_value=(MagicMock(), "TOKEN", "FWUID"),
        ),
        patch("oomi_influx.fetch.fetch_consumption") as mock_fetch,
    ):
        from oomi_influx.fetch import SessionExpiredError

        mock_fetch.side_effect = [SessionExpiredError("expired"), [RECORD]]
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)

        records = oomi.get_consumption(start, end)

    assert mock_login.call_count == 2  # initial + reauth
    assert records == [RECORD]


def test_get_consumption_no_reauth_needed(settings: Settings) -> None:
    oomi = OomiClient(settings)

    with (
        patch("oomi_influx.client.form_login", return_value="SID") as mock_login,
        patch(
            "oomi_influx.client.establish_session",
            return_value=(MagicMock(), "TOKEN", "FWUID"),
        ),
        patch("oomi_influx.fetch.fetch_consumption", return_value=[RECORD]),
    ):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        records = oomi.get_consumption(start, end)

    assert mock_login.call_count == 1
    assert records == [RECORD]
