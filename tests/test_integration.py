"""Integration tests against the live Oomi service.

Requires a populated .env file with real OOMI_* credentials.

Run:   uv run pytest -m integration
Skip:  excluded from the default 'uv run pytest' run.
"""

from datetime import datetime, timedelta, timezone

import pytest

from oomi_influx.auth import establish_session, form_login
from oomi_influx.config import Settings
from oomi_influx.fetch import fetch_consumption


def _load_settings() -> Settings | None:
    try:
        return Settings()  # ty:ignore[missing-argument]
    except Exception:
        return None


@pytest.fixture(scope="module")
def settings() -> Settings:
    s = _load_settings()
    if s is None:
        pytest.skip("No .env credentials — set OOMI_USERNAME, OOMI_PASSWORD, etc.")
    return s


@pytest.fixture(scope="module")
def live_session(settings: Settings):
    """Establish one real session shared across all integration tests."""
    sid = form_login(settings.username, settings.password, settings.base_url)
    client, token, fwuid = establish_session(sid, settings.base_url)
    yield client, token, fwuid
    client.close()


pytestmark = pytest.mark.integration


def test_form_login_returns_session_id(settings: Settings) -> None:
    sid = form_login(settings.username, settings.password, settings.base_url)
    assert sid, "form_login returned empty session ID"
    assert len(sid) > 10, f"Session ID looks too short: {sid!r}"


def test_establish_session_returns_token_and_fwuid(settings: Settings) -> None:
    sid = form_login(settings.username, settings.password, settings.base_url)
    client, token, fwuid = establish_session(sid, settings.base_url)
    client.close()

    assert token.count(".") >= 2, f"aura_token doesn't look like a JWT: {token!r}"
    assert len(token) > 20, f"aura_token looks too short: {token!r}"
    assert fwuid, "fwuid is empty"
    assert len(fwuid) > 5, f"fwuid looks too short: {fwuid!r}"


def test_fetch_consumption_returns_realistic_records(
    live_session, settings: Settings
) -> None:
    client, token, fwuid = live_session
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=2)

    records = fetch_consumption(client, token, fwuid, settings, start, end)

    assert len(records) > 0, (
        "No records returned for the past 48 hours. "
        "Either no data exists yet or parsing is broken."
    )

    for r in records:
        assert r.timestamp.tzinfo is not None, "Timestamp has no timezone info"
        assert start <= r.timestamp <= end, (
            f"Timestamp {r.timestamp} is outside the requested range [{start}, {end}]"
        )
        assert r.kwh >= 0, f"Negative kWh: {r.kwh}"
        assert r.kwh < 50, f"Implausibly large kWh for a 15-min slot: {r.kwh}"


def test_fetch_consumption_timestamps_are_15min_apart(
    live_session, settings: Settings
) -> None:
    client, token, fwuid = live_session
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(hours=4)

    records = fetch_consumption(client, token, fwuid, settings, start, end)

    if len(records) < 2:
        pytest.skip("Too few records to check spacing")

    for prev, curr in zip(records, records[1:]):
        gap = (curr.timestamp - prev.timestamp).total_seconds()
        assert gap == 15 * 60, (
            f"Expected 15-min gap between records, got {gap}s "
            f"({prev.timestamp} → {curr.timestamp})"
        )
