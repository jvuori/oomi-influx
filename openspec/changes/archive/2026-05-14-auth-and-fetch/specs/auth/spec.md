# Spec: auth

## Purpose

Verify Oomi credentials and establish a headless Salesforce session.

## Requirements

### Credentials

- REQ-AUTH-01: Credentials (`OOMI_USERNAME`, `OOMI_PASSWORD`) are read from environment
  variables / `.env` via `Settings`. No credential storage step is performed; credentials
  are always sourced from the environment at runtime.

### Form login

- REQ-AUTH-02: `form_login(username, password) -> str` POSTs to `BASE_URL/login`
  with form fields `username`, `un` (JS copies username→un before submit), `pw`, and
  standard Salesforce community login parameters (`startURL`, `lt`, `Login`, `useSecure`,
  `hasRememberUn`, `display`). Returns the `sessionId` from the `sid=` query parameter
  of the 302 redirect to `frontdoor.jsp`.
- REQ-AUTH-03: On non-redirect response (login page re-displayed, bad credentials),
  raises `LoginError`.

### Session establishment

- REQ-AUTH-04: `establish_session(session_id) -> tuple[httpx.Client, str, str]` performs:
  1. GET `BASE_URL/secur/frontdoor.jsp?sid={session_id}&retURL=/s/` with `follow_redirects=True`.
  2. GET `BASE_URL/s/` on the resulting client (cookie jar carries the community session cookie).
  3. Reads `aura_token` from the first cookie whose name contains `ERIC`
     (`__Host-ERIC_PROD...`). This JWT is the Aura CSRF token set by the server.
  4. Extracts `fwuid` from the `aura_prod.js` script URL in the `/s/` HTML via regex
     `/sfsites/auraFW/javascript/<FWUID>/aura_prod.js`.
  5. Returns `(client, aura_token, fwuid)`.
- REQ-AUTH-05: If the ERIC cookie is absent, raises `AuraTokenNotFound`.
- REQ-AUTH-06: If the fwuid regex does not match, raises `FwuidNotFound`.

### CLI — `auth login`

- REQ-AUTH-07: `oomi-influx auth login` reads credentials from `Settings` (env vars /
  `.env`), calls `form_login` to verify they work, and prints a success message.
- REQ-AUTH-08: Exits non-zero on `LoginError` with the error message.
