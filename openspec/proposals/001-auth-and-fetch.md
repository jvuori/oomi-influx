# Proposal 001 — Auth, credential management, and initial consumption fetch

## Problem

Oomi's customer portal (oma.oomi.fi) is a Salesforce Experience Cloud application.
There is no published API. Data must be retrieved by replaying the browser's Aura
action calls over raw HTTP. This requires:

1. A headless login mechanism (no browser, no GUI).
2. Secure local storage of the Oomi username and password.
3. A session-management layer that keeps the Salesforce session alive and re-authenticates on expiry.
4. A thin data-fetch layer that calls the `oomi_ConsumptionController.getConsumption`
   Aura action and returns raw consumption + spot-price records.

## Proposed solution

### CLI entry point — `oomi-influx`

A single `oomi-influx` CLI (via `uv run oomi-influx …`) with two subcommands for
this phase:

| Command | Purpose |
|---|---|
| `oomi-influx auth login` | Interactive: prompt for username + password, verify via SOAP login, store to OS keyring |
| `oomi-influx fetch consumption` | Headless: load credentials, establish session, call getConsumption, print NDJSON to stdout |

### Authentication flow (headless after initial setup)

```
1. Keyring load    → (username, password)
2. SOAP POST       /services/Soap/u/59.0   → sessionId
3. GET             /secur/frontdoor.jsp?sid={sessionId}&retURL=/s/
4. GET             /s/                     → HTML; regex-extract aura.token JWT
5. POST            /s/sfsites/aura         → NDJSON consumption rows
   On 401/redirect → re-authenticate from step 2
```

### Credential storage

- `keyring` library — writes to OS keyring (libsecret / macOS Keychain / Windows Credential Store).
- Service name: `oomi-influx`; username key: the Oomi login email.
- One-time config values that are **not** secrets (GSRN meter EAN, `customerIdentification`) are stored in `.env` (git-ignored); `.env.example` carries placeholder keys.

### Module layout

```
src/oomi_influx/
  auth.py        # keyring load/save, SOAP login, frontdoor handshake, aura.token extraction
  session.py     # thin wrapper: holds session cookie + aura.token; auto-retries on expiry
  fetch.py       # build + fire getConsumption Aura call; parse NDJSON → list[ConsumptionRecord]
  models.py      # ConsumptionRecord dataclass (st, kwh, spot_eur_mwh)
  cli.py         # Typer app: auth login, fetch consumption
```

### Key dependencies

| Package | Role |
|---|---|
| `httpx` | All HTTP (sync) |
| `keyring` | OS credential storage |
| `typer` | CLI |
| `python-dotenv` | Load `.env` |
| `pydantic` | Runtime validation of env config |

No browser automation dependency of any kind.

## Non-goals

- InfluxDB writes — out of scope for this phase.
- Scheduling / daemon loop — out of scope; caller drives `fetch consumption`.
- Spot-price-only endpoint — `getConsumption` returns both; no separate call needed.
- OAuth2 / PKCE — Oomi does not expose this; SOAP login is the only headless path.
- Multi-account / multi-meter support — single GSRN only for now.

## Tasks

1. **Scaffold project** — `uv init`, `pyproject.toml`, `src/oomi_influx/__init__.py`, `.env.example`, `.gitignore`. (~30 min)
2. **`auth.py`** — SOAP login, frontdoor GET, aura.token extraction, keyring helpers. (~60 min)
3. **`session.py`** — session state container + auto-reauth on expiry. (~30 min)
4. **`fetch.py` + `models.py`** — Aura POST, NDJSON parse, `ConsumptionRecord`. (~45 min)
5. **`cli.py`** — `auth login` (interactive) and `fetch consumption` (headless). (~30 min)
6. **Tests** — mock HTTP responses for auth flow and fetch; keyring patched. (~45 min)
