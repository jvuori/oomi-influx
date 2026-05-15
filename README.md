# oomi-influx

Headless ETL tool that pulls 15-minute electricity consumption data from the
[Oomi](https://www.oma.oomi.fi) customer portal and writes it directly to InfluxDB 2.x.

No browser. No GUI. Designed to run unattended on a Raspberry Pi or any Linux server.

## How it works

Oomi's portal runs on Salesforce Experience Cloud and exposes no public API.
`oomi-influx` replays the same HTTP calls the browser makes:

1. Form-POST login → Salesforce session ID
2. Frontdoor handshake → community session cookie + Aura token
3. POST to the Aura API (`oomi_ConsumptionController.getConsumption`) → NDJSON

Each consumption slot is a 15-minute UTC-timestamped record written to InfluxDB as:

| InfluxDB concept | Value |
|---|---|
| Measurement | `electricity_consumption` (configurable) |
| Tag | `metering_point=<value>` (configurable) |
| Fields | `consumption_kwh`, `consumption_wh`, `resolution` (configurable) |

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Oomi customer account with smart meter access
- InfluxDB 2.x instance

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

### Oomi

| Variable | Description |
|---|---|
| `OOMI_GSRN` | Your meter EAN (18-digit number on your electricity contract) |
| `OOMI_CUSTOMER_ID` | Salesforce customer identifier (visible in portal network traffic) |
| `OOMI_USERNAME` | Your Oomi login email |
| `OOMI_PASSWORD` | Your Oomi password |

#### Finding OOMI_CUSTOMER_ID

Open the Oomi portal in a browser, navigate to the consumption page, and inspect
network requests in DevTools. Look for a POST to `sfsites/aura` and find
`customerIdentification` in the request payload.

### InfluxDB

| Variable | Description | Default |
|---|---|---|
| `INFLUX_URL` | InfluxDB base URL | — |
| `INFLUX_TOKEN` | API token with write access to the bucket | — |
| `INFLUX_ORG` | Organisation name | — |
| `INFLUX_BUCKET` | Destination bucket | — |
| `INFLUX_MEASUREMENT` | Measurement name | `electricity_consumption` |
| `INFLUX_TAG_KEY` | Tag key | `metering_point` |
| `INFLUX_TAG_VALUE` | Tag value (your meter identifier) | — |
| `INFLUX_FIELD_KWH` | Field name for kWh value | `consumption_kwh` |
| `INFLUX_FIELD_WH` | Field name for Wh value | `consumption_wh` |
| `INFLUX_FIELD_RESOLUTION` | Field name for slot resolution | `resolution` |

> **Never commit `.env`** — it is git-ignored. The repository is public.

## Usage

### Verify credentials

```bash
uv run oomi-influx auth login
```

Exits 0 and prints `Credentials OK.` on success; exits 1 with an error message on failure.

### Fetch consumption data (stdout)

```bash
# Last 7 days (default)
uv run oomi-influx fetch consumption

# Specific range
uv run oomi-influx fetch consumption --start 2026-05-01T00:00:00Z --end 2026-05-14T00:00:00Z
```

Output is NDJSON on stdout, one record per line:

```json
{"timestamp": "2026-05-14T06:00:00+00:00", "kwh": 0.662}
```

### Write consumption data to InfluxDB

```bash
# Last 7 days (default)
uv run oomi-influx write consumption

# Specific range
uv run oomi-influx write consumption --start 2026-05-01T00:00:00Z --end 2026-05-14T00:00:00Z
```

Fetches from Oomi and writes directly to the configured InfluxDB bucket in one step.

## Running on a schedule

### systemd timer (recommended for servers)

Create `/etc/systemd/system/oomi-influx.service`:

```ini
[Unit]
Description=Fetch and write Oomi consumption data to InfluxDB

[Service]
Type=oneshot
User=<your-user>
WorkingDirectory=/path/to/oomi-influx
EnvironmentFile=/path/to/oomi-influx/.env
ExecStart=uv run oomi-influx write consumption
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
0 * * * * cd /path/to/oomi-influx && uv run oomi-influx write consumption
```

## Development

### Run tests

```bash
# Unit tests (no network, no Docker needed)
uv run pytest

# InfluxDB integration tests (requires Docker)
uv run pytest -m integration

# InfluxDB integration tests against a pre-provisioned instance
INFLUX_TEST_URL=http://localhost:8086 \
INFLUX_TEST_TOKEN=<token> \
INFLUX_TEST_ORG=<org> \
uv run pytest -m integration
```

### Lint and type-check

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check .
```

All checks must pass before committing.

### Debugging login or API issues

Use the `/oomi:debug` skill in Claude Code. It opens the Oomi portal in a browser via
Playwright, captures live network traffic, and compares it to what the code expects.
