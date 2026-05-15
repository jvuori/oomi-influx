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

Run the interactive setup wizard — it logs in, fetches your meter details
automatically, and writes `.env` for you:

```bash
uv run oomi-influx configure
```

The wizard prompts for each setting and uses existing `.env` values as defaults,
so re-running it only asks you to confirm or change individual values.

### Environment variables

All settings can also be set manually in `.env`. Use `.env.example` as a template:

```bash
cp .env.example .env
```

#### Oomi

| Variable | Description |
|---|---|
| `OOMI_USERNAME` | Your Oomi login email |
| `OOMI_PASSWORD` | Your Oomi password |
| `OOMI_GSRN` | Your meter EAN (18-digit; fetched automatically by `configure`) |
| `OOMI_CUSTOMER_ID` | Salesforce customer identifier (fetched automatically by `configure`) |

#### InfluxDB

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and how to work
with Claude Code AI skills used in this project.
