# Spec: consumption-fetch

## Purpose

Retrieve consumption records from Oomi for a given date range and
meter point, returning typed Python objects.

## Data model

```python
@dataclass
class ConsumptionRecord:
    timestamp: datetime   # UTC, start of 15-min slot
    kwh: float            # energy consumed (kWh), field bn01
```

## Requirements

### Config

- REQ-FETCH-01: Runtime config loaded from environment / `.env`:
  - `OOMI_GSRN` — meter EAN (e.g. `643000000000000000`)
  - `OOMI_CUSTOMER_ID` — Salesforce `customerIdentification` field value
  - `OOMI_BASE_URL` — default `https://www.oma.oomi.fi` (overridable for testing)

### Fetch function

- REQ-FETCH-02: `fetch_consumption(client, aura_token, gsrn, customer_id, start, end) -> list[ConsumptionRecord]`
  POSTs to `/s/sfsites/aura?r=1&aura.ApexAction.execute=1` with:
  - `message` JSON: `oomi_ConsumptionController.getConsumption`, period `PT15M`,
    `fetchParams: ["Consumption"]`, `readingTypes: ["BN01"]`.
  - `aura.token` from the session.
  - `aura.pageURI`: `/s/consumption?gsrn={gsrn}`.
- REQ-FETCH-03: Parses the NDJSON response body (one JSON object per line) into
  `ConsumptionRecord` instances; skips lines where `bn01` is `null`.
- REQ-FETCH-04: On HTTP 4xx that indicates session expiry (redirect to `/s/login` in
  response or status 401), raises `SessionExpiredError`.

### Session wrapper

- REQ-FETCH-05: `OomiSession.get_consumption(start, end) -> list[ConsumptionRecord]`
  calls `fetch_consumption`; on `SessionExpiredError` re-authenticates once via
  `auth.soap_login` + `auth.establish_session` and retries exactly once.

### CLI — `fetch consumption`

- REQ-FETCH-06: `oomi-influx fetch consumption [--start ISO] [--end ISO]` calls
  `OomiSession.get_consumption` and writes NDJSON to stdout (one record per line as
  `{"timestamp": "...", "kwh": ...}`).
- REQ-FETCH-07: Defaults: `--start` = 7 days ago 00:00 UTC; `--end` = now UTC.
- REQ-FETCH-08: Exits non-zero on `CredentialsNotFound` with a clear message
  directing the user to run `oomi-influx auth login`.
