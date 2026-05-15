## 1. Dependencies & Config

- [x] 1.1 Add `influxdb-client` to project dependencies: `uv add influxdb-client`
- [x] 1.2 Add `testcontainers` to dev dependencies: `uv add --dev testcontainers`
- [x] 1.3 Add `InfluxSettings(BaseSettings)` class to `config.py` with `env_prefix="INFLUX_"` and fields `url`, `token`, `org`, `bucket`
- [x] 1.4 Append `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET` to `.env.example`

## 2. Write Module

- [x] 2.1 Create `src/oomi_influx/influx.py` with `write_consumption(records, settings, gsrn)` implementing the measurement schema (measurement=`consumption`, tag=`gsrn`, field=`kwh` as float, timestamp from record)

## 3. CLI

- [x] 3.1 Add `write_app` Typer sub-app to `cli.py`; register it as `app.add_typer(write_app, name="write")`
- [x] 3.2 Implement `write consumption` command: load `Settings` + `InfluxSettings`, call `OomiSession.get_consumption`, then `write_consumption`; handle config/session errors with non-zero exit

## 4. Integration Tests

- [x] 4.1 Add `influxdb` integration marker to `pyproject.toml` pytest `markers` list and update `addopts` to also exclude the new marker pattern if needed
- [x] 4.2 Create `tests/conftest_influx.py` (or extend `tests/conftest.py`) with a session-scoped `influx_settings` fixture: use `INFLUX_TEST_URL` env var if set (CI path), otherwise start an InfluxDB 2.x container via `testcontainers`; create and tear down a unique test bucket
- [x] 4.3 Write `tests/test_influx_write.py` with `@pytest.mark.integration` test that calls `write_consumption` with sample `ConsumptionRecord` data and queries the bucket to verify round-trip correctness (point count, `kwh` values, timestamps)
