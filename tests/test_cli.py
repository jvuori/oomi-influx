import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from oomi_influx.cli import app
from oomi_influx.models import ConsumptionRecord, CredentialsNotFound, LoginError

runner = CliRunner()

RECORD = ConsumptionRecord(
    timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    kwh=0.237,
    spot_eur_mwh=108.72,
)


def test_auth_login_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")

    with (
        patch("oomi_influx.cli.form_login", return_value="SID"),
        patch("oomi_influx.cli.store_credentials") as mock_store,
    ):
        result = runner.invoke(app, ["auth", "login"], input="u@x.com\nsecret\n")

    assert result.exit_code == 0, result.output
    assert "stored" in result.output.lower()
    mock_store.assert_called_once_with("u@x.com", "secret")


def test_auth_login_bad_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")

    with patch("oomi_influx.cli.form_login", side_effect=LoginError("Invalid login")):
        result = runner.invoke(app, ["auth", "login"], input="u@x.com\nwrong\n")

    assert result.exit_code == 1
    assert "Invalid login" in result.output


def test_fetch_consumption_stdout_ndjson(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")

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


def test_fetch_consumption_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")

    with patch("oomi_influx.cli.OomiSession") as MockSession:
        MockSession.return_value.get_consumption.side_effect = CredentialsNotFound(
            "Run auth login"
        )
        result = runner.invoke(app, ["fetch", "consumption"])

    assert result.exit_code == 1
    assert "Run auth login" in result.output
