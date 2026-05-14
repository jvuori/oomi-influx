# oomi-influx

Headless ETL tool that pulls 15-minute electricity consumption data from the
[Oomi](https://www.oma.oomi.fi) customer portal and emits NDJSON to stdout, ready
to be piped into InfluxDB or any other time-series store.

No browser. No GUI. Designed to run unattended on a Raspberry Pi or any Linux server.

## How it works

Oomi's portal runs on Salesforce Experience Cloud and exposes no public API.
`oomi-influx` replays the same HTTP calls the browser makes:

1. Form-POST login → Salesforce session ID
2. Frontdoor handshake → community session cookie + Aura token
3. POST to the Aura API (`oomi_ConsumptionController.getConsumption`) → NDJSON

Each output line is one 15-minute consumption slot:

```json
{"timestamp": "2026-05-14T06:00:00+00:00", "kwh": 0.662}
```

Timestamps are UTC, `kwh` uses `Decimal` precision internally and is serialised as a
JSON number.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Oomi customer account with smart meter access

## Installation

```bash
git clone <repo-url>
cd oomi-influx
uv sync
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `OOMI_GSRN` | Your meter EAN (18-digit number on your electricity contract) |
| `OOMI_CUSTOMER_ID` | Salesforce customer identifier (visible in portal network traffic) |
| `OOMI_USERNAME` | Your Oomi login email |
| `OOMI_PASSWORD` | Your Oomi password |

> **Never commit `.env`** — it is git-ignored. The repository is public.

### Finding OOMI_CUSTOMER_ID

Open the Oomi portal in a browser, navigate to the consumption page, and inspect
network requests in DevTools. Look for a POST to `sfsites/aura` and find
`customerIdentification` in the request payload.

## Usage

### Verify credentials

```bash
uv run oomi-influx auth login
```

Exits 0 and prints `Credentials OK.` on success; exits 1 with an error message on failure.

### Fetch consumption data

```bash
# Last 7 days (default)
uv run oomi-influx fetch consumption

# Specific range
uv run oomi-influx fetch consumption --start 2026-05-01T00:00:00Z --end 2026-05-14T00:00:00Z
```

Output is NDJSON on stdout, one record per line. Pipe it wherever you need:

```bash
uv run oomi-influx fetch consumption | influx write --bucket energy --org myorg
```

### Options

```
oomi-influx fetch consumption --help

  --start  ISO 8601 UTC datetime. Default: 7 days ago at 00:00 UTC.
  --end    ISO 8601 UTC datetime. Default: now.
```

## Running on a schedule

### systemd timer (recommended for servers)

Create `/etc/systemd/system/oomi-influx.service`:

```ini
[Unit]
Description=Fetch Oomi consumption data

[Service]
Type=oneshot
User=<your-user>
WorkingDirectory=/path/to/oomi-influx
EnvironmentFile=/path/to/oomi-influx/.env
ExecStart=uv run oomi-influx fetch consumption
StandardOutput=append:/var/log/oomi-influx.ndjson
```

Create `/etc/systemd/system/oomi-influx.timer`:

```ini
[Unit]
Description=Run oomi-influx every hour

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now oomi-influx.timer
```

### cron

```cron
0 * * * * cd /path/to/oomi-influx && uv run oomi-influx fetch consumption >> /var/log/oomi-influx.ndjson
```

## Development

### Run tests

```bash
# Unit tests (no network, no credentials needed)
uv run pytest

# Integration tests (requires populated .env, hits live Oomi service)
uv run pytest -m integration
```

### Lint and type-check

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check .
```

All four checks must pass before committing (enforced by `AGENTS.md`).

### Debugging login or API issues

Use the `/oomi:debug` skill in Claude Code. It opens the Oomi portal in a browser via
Playwright, captures live network traffic, and compares it to what the code expects.
