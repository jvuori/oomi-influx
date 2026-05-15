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

`write_consumption(records: list[ConsumptionRecord], settings: InfluxSettings, metering_point: str) -> None`
SHALL write each record to InfluxDB using the following schema:
- **measurement**: `electricity_consumption`
- **tag**: `metering_point` (value from the `metering_point` argument)
- **fields**:
  - `consumption_kwh` (`float`, cast from `Decimal`)
  - `consumption_wh` (`float`, `consumption_kwh × 1000`)
  - `resolution` (`str`, always `"PT15MIN"`)
- **timestamp**: `record.timestamp` (UTC, nanosecond precision)

The `metering_point` value is derived from the GSRN as `gsrn[-8:-1]`
(7-digit meter identifier, stripping the GS1 prefix and check digit).

The function SHALL use batch writes and close the client on completion.

#### Scenario: Write succeeds
- **WHEN** `write_consumption` is called with a non-empty list and valid settings
- **THEN** each record appears as a point in the InfluxDB bucket with measurement `electricity_consumption`, tag `metering_point`, and fields `consumption_kwh`, `consumption_wh`, `resolution`

#### Scenario: Empty list
- **WHEN** `write_consumption` is called with an empty list
- **THEN** the function returns without error and writes nothing to InfluxDB

#### Scenario: Client closed after write
- **WHEN** `write_consumption` completes (success or exception)
- **THEN** the InfluxDB client is closed

### Requirement: Metering point derivation

`Settings.metering_point` SHALL be a computed field derived from `Settings.gsrn` as
`gsrn[-8:-1]` — the 7-digit meter identifier embedded in the 18-digit GSRN, excluding
the trailing check digit.

#### Scenario: Metering point from GSRN
- **WHEN** `OOMI_GSRN=YOUR_GSRN_HERE` is configured
- **THEN** `Settings().metering_point == "YOUR_METERING_POINT_HERE"`

### Requirement: CLI `write consumption` subcommand

`oomi-influx write consumption [--start ISO] [--end ISO]` SHALL:
1. Load `Settings` (Oomi) and `InfluxSettings` (InfluxDB).
2. Call `OomiSession.get_consumption(start, end)`.
3. Call `write_consumption(records, influx_settings, settings.metering_point)`.
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
