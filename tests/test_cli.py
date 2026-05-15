import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from oomi_influx.cli import app
from oomi_influx.client import LoginError
from oomi_influx.models import AccountInfo, ConsumptionRecord

runner = CliRunner()

RECORD = ConsumptionRecord(
    timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    kwh=Decimal("0.237"),
)

_CONFIGURE_INFLUX_INPUT = "\nmytoken\nmyorg\nmybucket\n\n\n\n\n\n\n"


def test_configure_success() -> None:
    fake_info = AccountInfo(
        customer_id="CUST123",
        gsrn="643000000000000000",
        first_name="Test",
        last_name="User",
    )
    with (
        patch("oomi_influx.cli.dotenv_values", return_value={}),
        patch("oomi_influx.cli.form_login", return_value="SID"),
        patch(
            "oomi_influx.cli.establish_session", return_value=(MagicMock(), "tok", "fw")
        ),
        patch("oomi_influx.cli.fetch_account_info", return_value=fake_info),
    ):
        with runner.isolated_filesystem():
            result = runner.invoke(
                app,
                ["configure"],
                input=f"u@x.com\nsecret\n{_CONFIGURE_INFLUX_INPUT}",
            )

    assert result.exit_code == 0, result.output
    assert "OK" in result.output
    assert "Test User" in result.output


def test_configure_bad_credentials() -> None:
    with (
        patch("oomi_influx.cli.dotenv_values", return_value={}),
        patch("oomi_influx.cli.form_login", side_effect=LoginError("Invalid login")),
    ):
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["configure"], input="u@x.com\nwrong\n")

    assert result.exit_code == 1
    assert "Invalid login" in result.output


def test_fetch_consumption_stdout_ndjson(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")

    with patch("oomi_influx.cli.OomiClient") as MockClient:
        MockClient.return_value.get_consumption.return_value = [RECORD]
        result = runner.invoke(
            app,
            [
                "fetch",
                "consumption",
                "--start",
                "2026-01-01T00:00:00Z",
                "--end",
                "2026-01-02T00:00:00Z",
            ],
        )

    assert result.exit_code == 0, result.output
    row = json.loads(result.output.strip())
    assert row["kwh"] == 0.237
    assert "spot_eur_mwh" not in row
    assert "2026-01-01" in row["timestamp"]


def test_fetch_consumption_login_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "bad")

    with patch("oomi_influx.cli.OomiClient") as MockClient:
        MockClient.return_value.get_consumption.side_effect = LoginError("bad creds")
        result = runner.invoke(app, ["fetch", "consumption"])

    assert result.exit_code == 1
    assert "bad creds" in result.output
