import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from oomi_influx.cli import app
from oomi_influx.models import ConsumptionRecord, LoginError

runner = CliRunner()

RECORD = ConsumptionRecord(
    timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    kwh=0.237,
    spot_eur_mwh=108.72,
)


def test_auth_login_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")

    with patch("oomi_influx.cli.form_login", return_value="SID"):
        result = runner.invoke(app, ["auth", "login"])

    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_auth_login_bad_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "wrong")

    with patch("oomi_influx.cli.form_login", side_effect=LoginError("Invalid login")):
        result = runner.invoke(app, ["auth", "login"])

    assert result.exit_code == 1
    assert "Invalid login" in result.output


def test_fetch_consumption_stdout_ndjson(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")

    with patch("oomi_influx.cli.OomiSession") as MockSession:
        MockSession.return_value.get_consumption.return_value = [RECORD]
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
    assert row["spot_eur_mwh"] == 108.72
    assert "2026-01-01" in row["timestamp"]


def test_fetch_consumption_login_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "bad")

    with patch("oomi_influx.cli.OomiSession") as MockSession:
        MockSession.return_value.get_consumption.side_effect = LoginError("bad creds")
        result = runner.invoke(app, ["fetch", "consumption"])

    assert result.exit_code == 1
    assert "bad creds" in result.output
