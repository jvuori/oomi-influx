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

- [uv](https://docs.astral.sh/uv/)
- An Oomi customer account with smart meter access
- InfluxDB 2.x instance

## Installation

Install as a persistent uv tool (puts `oomi-influx` on your `PATH`):

```bash
uv tool install oomi-influx
```

To try it without installing:

```bash
uvx oomi-influx --help
```

## Configuration

Create a directory to hold the configuration, then run the interactive setup
wizard from it. The wizard logs in, fetches your meter details automatically,
and writes `.env` to the current directory:

```bash
mkdir ~/oomi-config && cd ~/oomi-config
oomi-influx configure
```

The wizard uses any existing `.env` values as defaults, so re-running it only
asks you to confirm or change individual values.

> **`.env` is read from the working directory.** Always run `oomi-influx` from
> the directory that contains your `.env`, or set the variables in your
> environment directly.

### Environment variables

`oomi-influx configure` writes all required variables to `.env` for you. If you
prefer to set them manually, create `.env` in your config directory with the
following variables:

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
oomi-influx fetch consumption

# Specific range
oomi-influx fetch consumption --start 2026-05-01T00:00:00Z --end 2026-05-14T00:00:00Z
```

Output is NDJSON on stdout, one record per line:

```json
{"timestamp": "2026-05-14T06:00:00+00:00", "kwh": 0.662}
```

### Write consumption data to InfluxDB

```bash
# Last 7 days (default)
oomi-influx write consumption

# Specific range
oomi-influx write consumption --start 2026-05-01T00:00:00Z --end 2026-05-14T00:00:00Z
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
WorkingDirectory=/home/<your-user>/oomi-config
ExecStart=oomi-influx write consumption
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

`WorkingDirectory` should point to the directory that contains your `.env`.
`oomi-influx` is the binary installed by `uv tool install` — confirm its path
with `which oomi-influx` and use the full path if systemd cannot find it.

### cron

```cron
# ┌─ minute (0 = top of the hour)
# │  ┌─ hour (every hour)
# │  │  ┌─ day of month (every day)
# │  │  │  ┌─ month (every month)
# │  │  │  │  ┌─ day of week (every day)
# │  │  │  │  │
  0  *  *  *  *  cd ~/oomi-config && oomi-influx write consumption
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and how to work
with Claude Code AI skills used in this project.
