import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from pathlib import Path
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


def test_setup_logging_adds_file_handler_regardless_of_existing_handlers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """File handler must be added for OOMI_INFLUX_LOG_FILE even when root already has handlers.

    Reproduces the production bug: if any handler exists on root (e.g. from pytest's logging
    plugin or a third-party library), `if root.handlers: return` causes _setup_logging() to
    exit before the RotatingFileHandler is ever attached.
    """
    import oomi_influx.cli as cli_mod

    log_file = tmp_path / "oomi.log"
    monkeypatch.setenv("OOMI_INFLUX_LOG_FILE", str(log_file))
    monkeypatch.setattr(cli_mod, "_logging_configured", False)
    # Root logger already has pytest's handlers at this point — do NOT clear them.
    assert logging.getLogger().handlers, "expected pytest handlers to be present"

    root = logging.getLogger()
    handlers_before = set(root.handlers)

    cli_mod._setup_logging()

    new_file_handlers = [
        h
        for h in root.handlers
        if isinstance(h, RotatingFileHandler) and h not in handlers_before
    ]
    # Cleanup before asserting so the file handle is closed on failure too
    for h in new_file_handlers:
        h.close()
        root.removeHandler(h)

    assert len(new_file_handlers) == 1, (
        "_setup_logging() must add a RotatingFileHandler even when root already has handlers"
    )


def test_log_timestamps_include_timezone_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Log timestamps must include a UTC offset so they are unambiguous."""
    import io
    import oomi_influx.cli as cli_mod

    monkeypatch.setattr(cli_mod, "_logging_configured", False)
    stream = io.StringIO()
    # Replace stderr with a buffer so we can inspect the formatted output
    monkeypatch.setattr("sys.stderr", stream)

    cli_mod._setup_logging()
    logging.getLogger("oomi_influx").info("test message")

    output = stream.getvalue()
    # Timezone offset looks like +0300 or -0500 or +0000
    import re

    assert re.search(r"[+-]\d{4}", output), (
        f"Expected UTC offset (e.g. +0300) in log output, got: {output!r}"
    )


def _start_from_call(mock_client: MagicMock) -> datetime:
    """Extract the resolved start datetime passed to get_consumption()."""
    args, _ = mock_client.return_value.get_consumption.call_args
    return args[0]


def _oomi_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OOMI_GSRN", "643000000000000000")
    monkeypatch.setenv("OOMI_CUSTOMER_ID", "CUST123")
    monkeypatch.setenv("OOMI_USERNAME", "u@x.com")
    monkeypatch.setenv("OOMI_PASSWORD", "secret")


def _influx_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every InfluxSettings field without a default.

    The CLI runs inside runner.isolated_filesystem() in these tests so the repo's
    own .env cannot stand in for a missing var -- that masked an incomplete
    fixture locally while CI, which has no .env, failed.
    """
    monkeypatch.setenv("INFLUX_URL", "http://localhost:8086")
    monkeypatch.setenv("INFLUX_TOKEN", "tok")
    monkeypatch.setenv("INFLUX_ORG", "org")
    monkeypatch.setenv("INFLUX_BUCKET", "bucket")
    monkeypatch.setenv("INFLUX_TAG_VALUE", "test-meter")


@pytest.mark.parametrize("command", [["fetch"], ["write"]])
def test_default_window_is_seven_days(
    command: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hourly default stays small; reconciliation uses an explicit --lookback-days."""
    _oomi_env(monkeypatch)
    _influx_env(monkeypatch)

    with (
        patch("oomi_influx.cli.OomiClient") as MockClient,
        patch("oomi_influx.cli.write_consumption"),
    ):
        MockClient.return_value.get_consumption.return_value = []
        with runner.isolated_filesystem():
            result = runner.invoke(app, [*command, "consumption"])

    assert result.exit_code == 0, result.output
    age_days = (datetime.now(tz=timezone.utc) - _start_from_call(MockClient)).days
    assert age_days in (7, 8), f"expected ~7-day lookback, got {age_days} days"


@pytest.mark.parametrize("command", [["fetch"], ["write"]])
def test_lookback_days_overrides_default_window(
    command: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """--lookback-days drives the daily reconciliation pass.

    Reproduces the production gap of 2026-08-07: Oomi backfilled two 15-minute
    slots after the 7-day rolling window had already moved past that day, so no
    run ever picked them up again. A 60-day reconciliation window catches them.
    """
    _oomi_env(monkeypatch)
    _influx_env(monkeypatch)

    with (
        patch("oomi_influx.cli.OomiClient") as MockClient,
        patch("oomi_influx.cli.write_consumption"),
    ):
        MockClient.return_value.get_consumption.return_value = []
        with runner.isolated_filesystem():
            result = runner.invoke(
                app, [*command, "consumption", "--lookback-days", "60"]
            )

    assert result.exit_code == 0, result.output
    start = _start_from_call(MockClient)
    age_days = (datetime.now(tz=timezone.utc) - start).days
    assert age_days in (60, 61), f"expected ~60-day lookback, got {age_days} days"
    assert (start.hour, start.minute, start.second) == (0, 0, 0)


@pytest.mark.parametrize("command", [["fetch"], ["write"]])
def test_start_and_lookback_days_are_mutually_exclusive(
    command: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Passing both is ambiguous — surface it rather than silently picking one."""
    _oomi_env(monkeypatch)
    _influx_env(monkeypatch)

    with patch("oomi_influx.cli.OomiClient") as MockClient:
        MockClient.return_value.get_consumption.return_value = []
        with runner.isolated_filesystem():
            result = runner.invoke(
                app,
                [
                    *command,
                    "consumption",
                    "--start",
                    "2026-01-01T00:00:00Z",
                    "--lookback-days",
                    "60",
                ],
            )

    assert result.exit_code != 0
    MockClient.return_value.get_consumption.assert_not_called()
