# Spec: auth

## Purpose

Store Oomi credentials securely and provide a headless Salesforce session.

## Requirements

### Credential storage

- REQ-AUTH-01: `store_credentials(username, password)` stores to OS keyring under
  service name `oomi-influx`.
- REQ-AUTH-02: `load_credentials()` returns `(username, password)` from OS keyring;
  raises `CredentialsNotFound` if absent.

### SOAP login

- REQ-AUTH-03: `soap_login(username, password) -> str` POSTs to
  `/services/Soap/u/59.0` and returns the `sessionId` from the XML response.
- REQ-AUTH-04: On SOAP fault (bad credentials, locked account), raises `LoginError`
  with the fault message.

### Session establishment

- REQ-AUTH-05: `establish_session(session_id) -> (httpx.Client, str)` performs:
  1. GET `/secur/frontdoor.jsp?sid={session_id}&retURL=/s/` with `follow_redirects=True`.
  2. GET `/s/` on the resulting client (cookie jar carries the session cookie).
  3. Extracts `aura.token` JWT from the HTML bootstrap via regex.
  4. Returns the live `httpx.Client` (with cookies) and the `aura.token` string.
- REQ-AUTH-06: If the `aura.token` pattern is not found in the HTML, raises
  `AuraTokenNotFound`.

### CLI — `auth login`

- REQ-AUTH-07: `oomi-influx auth login` prompts for username and password (password
  input is hidden), calls `soap_login` to verify, then calls `store_credentials`.
- REQ-AUTH-08: Prints a success message; exits non-zero on `LoginError`.
