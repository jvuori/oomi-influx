### Requirement: InfluxDB config

Runtime config SHALL be loaded from environment / `.env`:
- `INFLUX_URL` — InfluxDB base URL (e.g. `http://localhost:8086`)
- `INFLUX_TOKEN` — API token with write access to the target bucket
- `INFLUX_ORG` — organisation name
- `INFLUX_BUCKET` — destination bucket name

Config SHALL be provided via a `InfluxSettings(BaseSettings)` class with
`env_prefix="INFLUX_"`, `env_file=".env"`, and `dotenv_filtering="match_prefix"`.

#### Scenario: All vars present
- **WHEN** all four `INFLUX_*` env vars are set
- **THEN** `InfluxSettings()` instantiates without error

#### Scenario: Missing var
- **WHEN** any `INFLUX_*` env var is absent
- **THEN** `InfluxSettings()` raises a `ValidationError`

### Requirement: Write consumption records

`write_consumption(records: list[ConsumptionRecord], settings: InfluxSettings) -> None`
SHALL write each record to InfluxDB using the schema defined in `InfluxSettings`:
- **measurement**: `settings.measurement` (default `electricity_consumption`)
- **tag**: `settings.tag_key` = `settings.tag_value` (default key `metering_point`)
- **fields**:
  - `settings.field_kwh` (`float`, cast from `Decimal`; default `consumption_kwh`)
  - `settings.field_wh` (`float`, value × 1000; default `consumption_wh`)
  - `settings.field_resolution` (`str`, always `"PT15MIN"`; default `resolution`)
- **timestamp**: `record.timestamp` (UTC, nanosecond precision)

The function SHALL use batch writes and close the client on completion.

#### Scenario: Write succeeds
- **WHEN** `write_consumption` is called with a non-empty list and valid settings
- **THEN** each record appears as a point in the InfluxDB bucket with the configured
  measurement, tag, and fields

#### Scenario: Empty list
- **WHEN** `write_consumption` is called with an empty list
- **THEN** the function returns without error and writes nothing to InfluxDB

#### Scenario: Client closed after write
- **WHEN** `write_consumption` completes (success or exception)
- **THEN** the InfluxDB client is closed

### Requirement: CLI `write consumption` subcommand

`oomi-influx write consumption [--start ISO] [--end ISO]` SHALL:
1. Load `Settings` (Oomi) and `InfluxSettings` (InfluxDB).
2. Call `OomiClient.get_consumption(start, end)`.
3. Call `write_consumption(records, influx_settings)`.
4. Exit zero on success.

Default date range SHALL match `fetch consumption`: `--start` = 7 days ago 00:00 UTC,
`--end` = now UTC.

#### Scenario: Successful write
- **WHEN** all env vars are set and Oomi/InfluxDB are reachable
- **THEN** the command exits 0 and records are written to the bucket

#### Scenario: Config error
- **WHEN** any required env var is missing
- **THEN** the command exits non-zero with a descriptive error message on stderr

#### Scenario: Oomi session error
- **WHEN** `LoginError` or `SessionExpiredError` is raised
- **THEN** the command exits non-zero with a descriptive error message on stderr

### Requirement: Integration test fixture

A session-scoped pytest fixture SHALL provide an `InfluxSettings` pointed at a live
InfluxDB instance. The fixture SHALL:
- Start an InfluxDB 2.x Docker container via `testcontainers` if `INFLUX_TEST_URL` is
  not set in the environment.
- Use `INFLUX_TEST_URL`, `INFLUX_TEST_TOKEN`, `INFLUX_TEST_ORG`, and
  `INFLUX_TEST_BUCKET` directly if they are set (CI / pre-provisioned instance).
- Create and tear down a unique test bucket to keep test data isolated.

Integration tests SHALL be marked `@pytest.mark.integration` so they can be excluded
with `-m "not integration"`.

#### Scenario: Local Docker run
- **WHEN** `INFLUX_TEST_URL` is not set and Docker is available
- **THEN** the fixture starts an InfluxDB container, runs tests against it, and stops the container on teardown

#### Scenario: CI / pre-provisioned instance
- **WHEN** `INFLUX_TEST_URL` (and related vars) are set
- **THEN** the fixture connects to that instance without starting a container

#### Scenario: Integration test round-trip
- **WHEN** `write_consumption` writes a list of records via the fixture's settings
- **THEN** querying the bucket returns the same number of points with matching `consumption_kwh` values and timestamps
