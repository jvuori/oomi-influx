## Why

The pipeline can fetch consumption data from Oomi but currently has no way to persist
it — the only output is NDJSON to stdout. Writing directly to InfluxDB closes the
loop and makes the tool production-useful.

## What Changes

- New `influx-write` capability: a function that accepts `list[ConsumptionRecord]`
  and writes points to an InfluxDB 2.x bucket.
- InfluxDB connection settings (`INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`,
  `INFLUX_BUCKET`) added to config and `.env.example`.
- New `write` subcommand under the existing CLI: `oomi-influx write consumption`.
- Integration tests that spin up InfluxDB via Docker and verify round-trip writes.

## Capabilities

### New Capabilities

- `influx-write`: Write `ConsumptionRecord` data points to an InfluxDB 2.x bucket,
  including measurement schema, tag/field mapping, and CLI entry point.

### Modified Capabilities

- `consumption-fetch`: No requirement changes — existing fetch output feeds the new
  write capability without modification.

## Impact

- **New dependency**: `influxdb-client` (Python).
- **Config**: four new env vars; `.env.example` updated.
- **CLI**: new `write consumption` subcommand.
- **Tests**: integration test suite requiring Docker (local) or a live InfluxDB
  endpoint (CI via env vars).

## Non-goals

- Backfill orchestration or scheduling — this change only adds the write primitive.
- Support for InfluxDB 1.x.
- Writing any measurement other than consumption (e.g. market prices).
