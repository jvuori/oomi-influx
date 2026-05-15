import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer

from .auth import form_login
from .config import InfluxSettings, Settings
from .influx import write_consumption
from .models import LoginError, SessionExpiredError
from .session import OomiSession

app = typer.Typer(no_args_is_help=True)
auth_app = typer.Typer(no_args_is_help=True)
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login() -> None:
    """Verify Oomi credentials from OOMI_USERNAME / OOMI_PASSWORD env vars."""
    try:
        settings = Settings()  # ty:ignore[missing-argument]
    except Exception as exc:
        typer.echo(f"Config error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("Verifying credentials…")
    try:
        form_login(settings.username, settings.password)
    except LoginError as exc:
        typer.echo(f"Login failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("Credentials OK.")


fetch_app = typer.Typer(no_args_is_help=True)
app.add_typer(fetch_app, name="fetch")


def _parse_dt(value: str | None, default: datetime) -> datetime:
    if value is None:
        return default
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@fetch_app.command("consumption")
def fetch_consumption(
    start: Annotated[
        Optional[str],
        typer.Option(
            "--start", help="Start datetime (ISO 8601 UTC). Default: 7 days ago."
        ),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option("--end", help="End datetime (ISO 8601 UTC). Default: now."),
    ] = None,
) -> None:
    """Fetch consumption records, emit NDJSON to stdout."""
    now = datetime.now(tz=timezone.utc)
    default_start = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    resolved_start = _parse_dt(start, default_start)
    resolved_end = _parse_dt(end, now)

    try:
        settings = Settings()  # ty:ignore[missing-argument]
    except Exception as exc:
        typer.echo(f"Config error: {exc}", err=True)
        raise typer.Exit(1)

    try:
        session = OomiSession(settings)
        records = session.get_consumption(resolved_start, resolved_end)
    except (LoginError, SessionExpiredError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    for record in records:
        sys.stdout.write(
            json.dumps(
                {"timestamp": record.timestamp.isoformat(), "kwh": float(record.kwh)}
            )
            + "\n"
        )


write_app = typer.Typer(no_args_is_help=True)
app.add_typer(write_app, name="write")


@write_app.command("consumption")
def write_consumption_cmd(
    start: Annotated[
        Optional[str],
        typer.Option(
            "--start", help="Start datetime (ISO 8601 UTC). Default: 7 days ago."
        ),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option("--end", help="End datetime (ISO 8601 UTC). Default: now."),
    ] = None,
) -> None:
    """Fetch consumption records and write them to InfluxDB."""
    now = datetime.now(tz=timezone.utc)
    default_start = (now - timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    resolved_start = _parse_dt(start, default_start)
    resolved_end = _parse_dt(end, now)

    try:
        settings = Settings()  # ty:ignore[missing-argument]
        influx_settings = InfluxSettings()  # ty:ignore[missing-argument]
    except Exception as exc:
        typer.echo(f"Config error: {exc}", err=True)
        raise typer.Exit(1)

    try:
        session = OomiSession(settings)
        records = session.get_consumption(resolved_start, resolved_end)
    except (LoginError, SessionExpiredError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    write_consumption(records, influx_settings, settings.metering_point)
    typer.echo(f"Wrote {len(records)} records to InfluxDB.")
