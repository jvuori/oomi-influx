import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from dotenv import dotenv_values

from .auth import establish_session, form_login
from .config import InfluxSettings, Settings
from .fetch import fetch_account_info
from .influx import write_consumption
from .models import LoginError, SessionExpiredError
from .session import OomiSession

app = typer.Typer(no_args_is_help=True)


@app.command()
def configure() -> None:
    """Interactive setup wizard — writes or updates .env with all settings."""
    existing = dotenv_values(".env")

    # --- Oomi credentials ---
    typer.echo("\n=== Oomi ===")
    username = typer.prompt(
        "Username (email)", default=existing.get("OOMI_USERNAME", "")
    )
    pw_prompt = (
        "Password (Enter to keep existing)"
        if existing.get("OOMI_PASSWORD")
        else "Password"
    )
    password = typer.prompt(
        pw_prompt, default=existing.get("OOMI_PASSWORD", ""), hide_input=True
    )

    typer.echo("\nVerifying credentials…")
    try:
        session_id = form_login(username, password)
    except LoginError as exc:
        typer.echo(f"Login failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("Credentials OK. Fetching account info…")
    gsrn = existing.get("OOMI_GSRN", "")
    customer_id = existing.get("OOMI_CUSTOMER_ID", "")
    name = ""
    try:
        client, aura_token, fwuid = establish_session(session_id)
        try:
            info = fetch_account_info(client, aura_token, fwuid)
        finally:
            client.close()
        name = f"{info.first_name} {info.last_name}"
        gsrn = info.gsrn
        customer_id = info.customer_id
        typer.echo(f"  Name:        {name}")
        typer.echo(f"  Customer ID: {customer_id}")
        typer.echo(f"  GSRN:        {gsrn}")
    except Exception as exc:
        typer.echo(f"Warning: could not fetch account info ({exc}).", err=True)
        if not gsrn:
            gsrn = typer.prompt("OOMI_GSRN (18-digit EAN)")
        if not customer_id:
            customer_id = typer.prompt("OOMI_CUSTOMER_ID")

    # --- InfluxDB settings ---
    typer.echo("\n=== InfluxDB ===")
    default_tag_value = gsrn[-8:-1] if gsrn else ""
    influx_url = typer.prompt(
        "URL", default=existing.get("INFLUX_URL", "http://localhost:8086")
    )
    token_prompt = (
        "Token (Enter to keep existing)" if existing.get("INFLUX_TOKEN") else "Token"
    )
    influx_token = typer.prompt(
        token_prompt, default=existing.get("INFLUX_TOKEN", ""), hide_input=True
    )
    influx_org = typer.prompt("Organisation", default=existing.get("INFLUX_ORG", ""))
    influx_bucket = typer.prompt("Bucket", default=existing.get("INFLUX_BUCKET", ""))
    influx_measurement = typer.prompt(
        "Measurement",
        default=existing.get("INFLUX_MEASUREMENT", "electricity_consumption"),
    )
    influx_tag_key = typer.prompt(
        "Tag key", default=existing.get("INFLUX_TAG_KEY", "metering_point")
    )
    influx_tag_value = typer.prompt(
        "Tag value", default=existing.get("INFLUX_TAG_VALUE", default_tag_value)
    )
    influx_field_kwh = typer.prompt(
        "Field kWh", default=existing.get("INFLUX_FIELD_KWH", "consumption_kwh")
    )
    influx_field_wh = typer.prompt(
        "Field Wh", default=existing.get("INFLUX_FIELD_WH", "consumption_wh")
    )
    influx_field_resolution = typer.prompt(
        "Field resolution",
        default=existing.get("INFLUX_FIELD_RESOLUTION", "resolution"),
    )

    # --- Write .env ---
    env_lines = [
        f"OOMI_USERNAME={username}",
        f"OOMI_PASSWORD={password}",
        f"OOMI_GSRN={gsrn}",
        f"OOMI_CUSTOMER_ID={customer_id}",
        "",
        f"INFLUX_URL={influx_url}",
        f"INFLUX_TOKEN={influx_token}",
        f"INFLUX_ORG={influx_org}",
        f"INFLUX_BUCKET={influx_bucket}",
        f"INFLUX_MEASUREMENT={influx_measurement}",
        f"INFLUX_TAG_KEY={influx_tag_key}",
        f"INFLUX_TAG_VALUE={influx_tag_value}",
        f"INFLUX_FIELD_KWH={influx_field_kwh}",
        f"INFLUX_FIELD_WH={influx_field_wh}",
        f"INFLUX_FIELD_RESOLUTION={influx_field_resolution}",
    ]
    with open(".env", "w") as f:
        f.write("\n".join(env_lines) + "\n")

    typer.echo("\n.env written.")


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

    write_consumption(records, influx_settings)
    typer.echo(f"Wrote {len(records)} records to InfluxDB.")
