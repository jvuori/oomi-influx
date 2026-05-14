## Why

Oomi's customer portal has no published API. Consumption data must be retrieved by
replaying the browser's Salesforce Aura action calls. Before anything can be written
to InfluxDB, we need a reliable, fully headless HTTP-only auth + fetch layer.

## What Changes

- New Python package `oomi_influx` scaffolded under `src/`.
- `oomi-influx auth login` CLI command: interactive credential capture → OS keyring.
- `oomi-influx fetch consumption` CLI command: headless session establishment → raw NDJSON to stdout.
- `.env` / `.env.example` for non-secret runtime config (GSRN, customer ID, date range).

## Capabilities

### New Capabilities

- `auth`: Store Oomi credentials in the OS keyring; perform SOAP login and Salesforce session handshake to prove the credentials work.
- `consumption-fetch`: Load credentials from env vars, establish a Salesforce session via raw HTTP, call `oomi_ConsumptionController.getConsumption`, and emit NDJSON records (timestamp, kWh).

### Modified Capabilities

*(none — greenfield)*

## Impact

- New runtime dependencies: `httpx`, `keyring`, `typer`, `python-dotenv`, `pydantic`.
- Dev dependencies: `ruff`, `ty`, `pytest`, `pytest-httpx`.
- No database writes, no scheduler — caller drives everything.

## Non-goals

- InfluxDB writes.
- Scheduling / daemon loop.
- Multi-meter / multi-account support.
- OAuth2 — Oomi does not expose it; SOAP login is the only headless path.
