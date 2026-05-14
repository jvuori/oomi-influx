# Tasks: auth-and-fetch

## Task 1 — Scaffold project

- [x] `uv init` with `src/` layout; `pyproject.toml` with `[project.scripts] oomi-influx = "oomi_influx.cli:app"`.
- [x] `src/oomi_influx/__init__.py` (empty).
- [x] `.env.example` with `OOMI_GSRN=`, `OOMI_CUSTOMER_ID=`, `OOMI_BASE_URL=https://www.oma.oomi.fi`.
- [x] `.gitignore` covering `.env`, `__pycache__`, `.venv`, `dist/`.
- [x] Add runtime deps: `httpx`, `keyring`, `typer`, `python-dotenv`, `pydantic`.
- [x] Add dev deps: `ruff`, `ty`, `pytest`, `pytest-httpx`.

## Task 2 — `models.py` and `config.py`

- [x] `ConsumptionRecord` dataclass (REQ-FETCH-02 data model).
- [x] `Settings` pydantic model loading `OOMI_GSRN`, `OOMI_CUSTOMER_ID`, `OOMI_BASE_URL` from env.
- [x] Custom exceptions: `CredentialsNotFound`, `LoginError`, `AuraTokenNotFound`, `SessionExpiredError`.

## Task 3 — `auth.py`

- [x] `store_credentials(username, password)` → OS keyring (REQ-AUTH-01).
- [x] `load_credentials() -> tuple[str, str]` → OS keyring (REQ-AUTH-02).
- [x] `soap_login(username, password, base_url) -> str` → sessionId (REQ-AUTH-03/04).
- [x] `establish_session(session_id, base_url) -> tuple[httpx.Client, str]` → (client, aura_token) (REQ-AUTH-05/06).

## Task 4 — `session.py`

- [x] `OomiSession` holding `client`, `aura_token`, `settings`.
- [x] `OomiSession.get_consumption(start, end)` with single auto-reauth on `SessionExpiredError` (REQ-FETCH-05).

## Task 5 — `fetch.py`

- [x] `fetch_consumption(client, aura_token, settings, start, end) -> list[ConsumptionRecord]` (REQ-FETCH-02/03/04).

## Task 6 — `cli.py`

- [x] `auth login` subcommand (REQ-AUTH-07/08).
- [x] `fetch consumption --start --end` subcommand (REQ-FETCH-06/07/08).

## Task 7 — Tests

- [x] `test_auth.py`: SOAP login success/fault; `establish_session` cookie+token; `load_credentials` missing.
- [x] `test_fetch.py`: `fetch_consumption` happy path; `SessionExpiredError` on redirect; null-kwh skip.
- [x] `test_session.py`: auto-reauth retry on `SessionExpiredError`.
- [x] `test_cli.py`: `auth login` happy + error; `fetch consumption` stdout NDJSON.
