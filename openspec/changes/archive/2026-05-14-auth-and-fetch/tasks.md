# Tasks: auth-and-fetch

## Task 1 — Scaffold project

- [x] `uv init` with `src/` layout; `pyproject.toml` with `[project.scripts] oomi-influx = "oomi_influx.cli:app"`.
- [x] `src/oomi_influx/__init__.py` (empty).
- [x] `.env.example` with `OOMI_GSRN=`, `OOMI_CUSTOMER_ID=`, `OOMI_BASE_URL=https://www.oma.oomi.fi`, `OOMI_USERNAME=`, `OOMI_PASSWORD=`.
- [x] `.gitignore` covering `.env`, `__pycache__`, `.venv`, `dist/`.
- [x] Add runtime deps: `httpx`, `typer`, `python-dotenv`, `pydantic`, `pydantic-settings`.
- [x] Add dev deps: `ruff`, `ty`, `pytest`, `pytest-httpx`.

## Task 2 — `models.py` and `config.py`

- [x] `ConsumptionRecord` dataclass with `timestamp: datetime` and `kwh: Decimal`.
- [x] `Settings` pydantic model loading `OOMI_GSRN`, `OOMI_CUSTOMER_ID`, `OOMI_BASE_URL`, `OOMI_USERNAME`, `OOMI_PASSWORD` from env.
- [x] Custom exceptions: `LoginError`, `AuraTokenNotFound`, `FwuidNotFound`, `SessionExpiredError`.

## Task 3 — `auth.py`

- [x] `form_login(username, password, base_url) -> str` → sessionId (REQ-AUTH-02/03).
- [x] `establish_session(session_id, base_url) -> tuple[httpx.Client, str, str]` → (client, aura_token, fwuid) (REQ-AUTH-04/05/06).

## Task 4 — `session.py`

- [x] `OomiSession` holding `client`, `aura_token`, `fwuid`, `settings`.
- [x] `OomiSession.get_consumption(start, end)` with single auto-reauth on `SessionExpiredError` (REQ-FETCH-05).

## Task 5 — `fetch.py`

- [x] `fetch_consumption(client, aura_token, fwuid, settings, start, end) -> list[ConsumptionRecord]` (REQ-FETCH-02/03/04).

## Task 6 — `cli.py`

- [x] `auth login` subcommand (REQ-AUTH-07/08).
- [x] `fetch consumption --start --end` subcommand (REQ-FETCH-06/07/08).

## Task 7 — Tests

- [x] `test_auth.py`: form login success/failure; `establish_session` ERIC cookie + fwuid extraction; `AuraTokenNotFound` on missing cookie; `FwuidNotFound` on missing fwuid.
- [x] `test_fetch.py`: `fetch_consumption` happy path; `SessionExpiredError` on 401; null-kwh rows skipped; Aura error response.
- [x] `test_session.py`: auto-reauth retry on `SessionExpiredError`.
- [x] `test_cli.py`: `auth login` happy + error; `fetch consumption` stdout NDJSON + login error exit.
- [x] `test_integration.py`: live service — form login, session establishment, realistic records, 15-min timestamp spacing.
