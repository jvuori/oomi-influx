## Context

The pipeline already fetches `ConsumptionRecord` objects from Oomi. The only missing
piece is persistence. The natural target is InfluxDB 2.x — the project name implies it
and the domain (15-min energy metering) is a canonical time-series workload.

Current state: config lives in a single `Settings(BaseSettings)` class with
`env_prefix="OOMI_"`. The CLI has two sub-apps (`auth`, `fetch`).

## Goals / Non-Goals

**Goals:**
- A `write_consumption` function that writes `list[ConsumptionRecord]` to InfluxDB.
- A second `InfluxSettings` Pydantic class for the four InfluxDB env vars.
- A `write consumption` CLI subcommand that fetches and writes in one step.
- Integration tests that run against a real InfluxDB instance, local or remote.

**Non-Goals:**
- Scheduling or orchestration.
- InfluxDB 1.x compatibility.
- Measurements beyond `consumption`.

## Decisions

### 1 — Separate `InfluxSettings` class

`OOMI_*` and `INFLUX_*` env vars serve distinct subsystems. A second
`InfluxSettings(BaseSettings)` with `env_prefix="INFLUX_"` keeps each class cohesive
and lets either subsystem be instantiated in isolation (e.g., tests that only need
InfluxDB).

### 2 — New `influx.py` module

Write logic lives in `src/oomi_influx/influx.py`:

```python
def write_consumption(
    records: list[ConsumptionRecord],
    settings: InfluxSettings,
    gsrn: str,
) -> None
```

`gsrn` is passed explicitly (sourced from `OomiSettings`) so the function has no
hidden dependency on Oomi config — it is a pure InfluxDB writer.

Measurement schema:
- **measurement**: `consumption`
- **tag**: `gsrn` (meter EAN — identifies the physical meter)
- **field**: `kwh` (float)
- **timestamp**: `record.timestamp` (UTC, nanosecond precision)

### 3 — `write consumption` CLI subcommand

A new `write_app` Typer sub-app with a `consumption` command that:
1. Loads both `Settings` and `InfluxSettings`.
2. Calls `OomiSession.get_consumption(start, end)`.
3. Calls `write_consumption(records, influx_settings, settings.gsrn)`.

This is a single ergonomic entry point for the common cron-job use case. Composing
`fetch consumption | write consumption` via stdin is explicitly a non-goal for this
change.

### 4 — Integration tests via `testcontainers`

`testcontainers` manages the Docker lifecycle, works identically locally and in CI
(any runner with Docker). A session-scoped fixture starts one InfluxDB 2.x container
per test run and yields a configured `InfluxSettings`. Tests are marked
`@pytest.mark.integration` so they can be skipped with `-m "not integration"` in
environments without Docker.

Alternatively, if `INFLUX_TEST_URL` (and related vars) are already set in the
environment, the fixture skips container startup and connects directly — this is the
CI-without-Docker escape hatch.

## Risks / Trade-offs

- **`testcontainers` container pull time** — first run pulls the InfluxDB image.
  Mitigated by layer caching in Docker and CI image caching.
- **Duplicate `gsrn` tag across test writes** — use a unique bucket per test session
  (created and torn down by the fixture) to keep test data isolated.
- **`kwh` as float in InfluxDB** — `Decimal` is cast to `float` at write time;
  InfluxDB stores IEEE 754 doubles. Precision loss is at most ~15 significant digits,
  acceptable for kWh readings.
