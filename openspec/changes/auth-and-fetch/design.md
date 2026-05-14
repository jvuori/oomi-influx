## Context

Oomi's portal is Salesforce Experience Cloud. The portal uses the Salesforce Aura
framework; all data calls go to `/s/sfsites/aura` as form-encoded POST requests
authenticated with a session cookie and an `aura.token` JWT embedded in the page HTML.

There is no OAuth2 endpoint exposed to external clients. The only headless login
path is the **Salesforce SOAP Login API** (`/services/Soap/u/59.0`), which accepts
username + password in an XML envelope and returns a `sessionId`. That session ID is
then handed off via `/secur/frontdoor.jsp` to set the community session cookie, after
which the `aura.token` can be scraped from the `/s/` HTML and used in Aura calls.

## Goals / Non-Goals

**Goals:**

- Headless re-authentication from keyring credentials with no browser dependency.
- Encapsulate session lifetime: auto-reauth on 401 or redirect-to-login.
- Thin CLI surface (`auth login`, `fetch consumption`) to drive manual testing.

**Non-Goals:**

- InfluxDB writes, scheduling, daemon loop.
- Multi-meter / multi-account.

## Decisions

### D1 — Credentials stored as username + password, not a session token

Sessions expire (hours); storing a session token would require re-login on every cold
start anyway. Storing username + password and re-authenticating via SOAP on demand is
simpler and equally secure given OS keyring protection.

*Alternative considered*: persist the session cookie between runs. Rejected: sessions
are short-lived (2–8 h), and persisting them adds state management complexity with no
meaningful latency benefit.

### D2 — `httpx` (sync) for all HTTP

`httpx` follows redirects, handles cookies via `httpx.Client`, and is well-established
in the Python data ecosystem. Async is not needed at this stage; a single sync client
with a cookie jar is sufficient.

*Alternative*: `requests`. Equivalent capability; `httpx` is preferred per project
conventions.

### D3 — `aura.token` extracted via regex from HTML bootstrap

The token is embedded as `"token":"<JWT>"` inside the Salesforce bootstrap JSON in
the `/s/` page HTML. A targeted regex is reliable and avoids an HTML-parser dependency.

### D4 — Non-secret config (GSRN, customerIdentification) in `.env`

GSRN and the Salesforce `customerIdentification` field are personal/account identifiers
(must never be committed per AGENTS.md) but do not need the extra encryption of OS
keyring. `.env` with `python-dotenv` is sufficient.

### D5 — Module layout

```
src/oomi_influx/
  __init__.py
  auth.py        # keyring helpers, SOAP login, frontdoor, aura.token extraction
  session.py     # OomiSession: holds client + token; auto-reauth wrapper
  fetch.py       # getConsumption Aura call + NDJSON parse → list[ConsumptionRecord]
  models.py      # ConsumptionRecord (dataclass / typed dict)
  config.py      # pydantic Settings loaded from .env
  cli.py         # Typer app: auth login, fetch consumption
```

## Risks / Trade-offs

- **SOAP endpoint availability**: Some Salesforce orgs restrict SOAP login to
  `login.salesforce.com` only. If `https://www.oma.oomi.fi/services/Soap/u/59.0`
  rejects community user credentials, the approach breaks. → *Mitigation*: verify
  with a live test immediately; if blocked, fall back to form-POST login scrape.

- **`aura.token` format change**: Salesforce releases are tri-annual; a release could
  change where the token appears in the bootstrap HTML. → *Mitigation*: regex failure
  raises a clear `AuraTokenNotFound` exception; easy to update the pattern.

- **Session cookie domain**: If `/secur/frontdoor.jsp` sets a cookie scoped to a
  subdomain different from `/s/sfsites/aura`'s host, the cookie won't attach. → *Mitigation*: `httpx.Client` with `follow_redirects=True`; inspect cookie jar in tests.
