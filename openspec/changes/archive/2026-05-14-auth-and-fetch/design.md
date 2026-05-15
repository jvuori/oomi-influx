## Context

Oomi's portal is Salesforce Experience Cloud (LWR / Aura). All data calls go to
`/s/sfsites/aura` as form-encoded POST requests authenticated with a community session
cookie and an `aura.token` JWT. There is no OAuth2 endpoint exposed to external clients.

The headless login path is a **form POST to `/login`** — the same request the browser
submits when the user clicks "Log In". A successful login returns a 302 redirect to
`/secur/frontdoor.jsp?sid=<sessionId>`, from which the community session is established.

## Goals / Non-Goals

**Goals:**

- Headless authentication from env-var credentials with no browser dependency.
- Encapsulate session lifetime: auto-reauth on 401 or redirect-to-login.
- Thin CLI surface (`auth login`, `fetch consumption`) to drive manual testing.

**Non-Goals:**

- InfluxDB writes, scheduling, daemon loop.
- Multi-meter / multi-account.

## Decisions

### D1 — Credentials in environment variables, not a session token

Sessions expire (hours); storing a session token would require re-login on every cold
start anyway. Storing username + password in env vars / `.env` and re-authenticating
via form POST on demand is simpler, and `.env` is already git-ignored per AGENTS.md.

*Alternative considered*: persist the session cookie between runs. Rejected: sessions
are short-lived (2–8 h), and persisting them adds state management complexity with no
meaningful latency benefit.

### D2 — `httpx` (sync) for all HTTP

`httpx` follows redirects, handles cookies via `httpx.Client`, and is well-established
in the Python data ecosystem. Async is not needed at this stage; a single sync client
with a cookie jar is sufficient.

*Alternative*: `requests`. Equivalent capability; `httpx` is preferred per project
conventions.

### D3 — `aura_token` from ERIC cookie; `fwuid` via regex on script URL

After the frontdoor handshake, the server sets a `__Host-ERIC_PROD...` cookie whose
value is the Aura CSRF token (a JWT). Reading it from the cookie jar is more reliable
than scraping HTML.

The Aura framework UID (`fwuid`) is extracted via regex from the `aura_prod.js` script
URL embedded in the `/s/` page HTML:
`/sfsites/auraFW/javascript/<FWUID>/aura_prod.js`.

### D4 — Non-secret config (GSRN, customerIdentification) in `.env`

GSRN and the Salesforce `customerIdentification` field are personal/account identifiers
(must never be committed per AGENTS.md) but do not need extra encryption. `.env` with
`pydantic-settings` is sufficient.

### D5 — Module layout

```
src/oomi_influx/
  __init__.py
  auth.py        # form_login, establish_session (ERIC cookie + fwuid extraction)
  session.py     # OomiSession: holds client + token + fwuid; auto-reauth wrapper
  fetch.py       # getConsumption Aura call + NDJSON parse → list[ConsumptionRecord]
  models.py      # ConsumptionRecord (dataclass); exception types
  config.py      # pydantic Settings loaded from env / .env
  cli.py         # Typer app: auth login, fetch consumption
```

## Risks / Trade-offs

- **ERIC cookie rename**: A Salesforce release could rename the `__Host-ERIC_PROD...`
  cookie. → *Mitigation*: the code matches any cookie containing `ERIC`; a rename
  that drops `ERIC` entirely will raise `AuraTokenNotFound` immediately with a clear
  message.

- **`fwuid` URL pattern change**: Salesforce releases are tri-annual; a release could
  change the `aura_prod.js` script URL structure. → *Mitigation*: regex failure raises
  `FwuidNotFound` immediately; the pattern is a one-line constant easy to update.

- **Login form field change**: If Oomi changes the login form fields (e.g. removes `un`),
  the POST will silently succeed with a non-redirect response and `LoginError` will be
  raised. → *Mitigation*: clear error message; `/oomi:debug` skill guides investigation.
