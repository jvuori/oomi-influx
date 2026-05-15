# Contributing to oomi-influx

## Development environment

Requirements: Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd oomi-influx
uv sync
```

That's it — `uv sync` creates the virtual environment and installs all dependencies.

## Running tests

```bash
# Unit tests (no network, no Docker needed)
uv run pytest

# InfluxDB integration tests (requires Docker)
uv run pytest -m integration

# InfluxDB integration tests against a pre-provisioned instance
INFLUX_TEST_URL=http://localhost:8086 \
INFLUX_TEST_TOKEN=<token> \
INFLUX_TEST_ORG=<org> \
uv run pytest -m integration
```

## Lint and type-check

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check .
```

All checks must pass before committing.

## Commit conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for hourly resolution
fix: handle missing meter data gracefully
refactor: split auth into separate module
docs: update README for new configure wizard
```

## AI-assisted development

This project uses [Claude Code](https://claude.ai/code) with custom skills. If you have
Claude Code set up, the following skills are available:

### `/oomi:debug`

Investigates Oomi portal API changes that break login or consumption fetching. Opens the
Oomi portal in a headless browser via Playwright, captures live network traffic, and
compares it to what the code expects. Use this when authentication or the Aura API
response format appears to have changed.

### `/opsx:propose`, `/opsx:apply`, `/opsx:explore`

OpenSpec workflow skills for planning and implementing changes. `propose` drafts a
design with tasks, `apply` implements the tasks one by one, and `explore` is a
free-form thinking partner for investigating a problem before committing to a solution.

## Project structure

```
oomi_influx/
  client/     # HTTP client: login, frontdoor handshake, Aura API calls
  fetch/      # CLI fetch commands (stdout NDJSON)
  _aura/      # Aura response parsing
  __main__.py # CLI entry point (click)
tests/
  unit/       # Pure-unit tests, no I/O
  integration/# Tests against a real InfluxDB instance
```

## Sensitive data

- Never commit `.env` — it is git-ignored and the repository is public.
- Never hardcode credentials, tokens, or meter identifiers in source files or tests.
- Use `.env.example` (no real values) as the reference for what variables exist.
