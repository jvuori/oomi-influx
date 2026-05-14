# Agent Rules

## Communication

- Always address the user as **"Principal"** in chat responses.

## Python tooling

- Use **`uv`** for all Python operations: adding packages, running scripts, tests, and any other Python invocations.
- Never call `python` directly — always via `uv run <command>`.
- Examples:
  - Run tests: `uv run pytest`
  - Add a dependency: `uv add <package>`
  - Run a script: `uv run python src/foo.py`

## Coding style

- Prefer **functional and procedural, Pythonic style**. Do not use Object-Oriented design unless a third-party API forces it.
- Add **type hints** to all function signatures and variables where the type is not immediately obvious.
- Keep modules small and focused; favour pure functions and explicit data passing over shared state.

## Dependencies

- Use only **well-established, high-reputation third-party packages**.
- Keep the dependency surface **as small as possible** — this is a library and consumers inherit every dependency.
- Prefer packages from the Python scientific / data ecosystem (e.g. `httpx`, `influxdb-client`, `pydantic`) over obscure alternatives.

## Linting and quality

Before every commit:

1. `uv run ruff check --fix .`
2. `uv run ruff format .`
3. `uv run ty check .`
4. `uv run pytest`

All four must pass with no errors before changes are committed.

## Git commit messages

- Never include `Co-Authored-By` lines in commit messages.

## Security — never commit personal or sensitive data

The following must **never** be stored in Git (this will be a public repository):

- Credentials, passwords, tokens, API keys, or secrets of any kind
- Personal data: names, email addresses, phone numbers
- Subscription IDs, account IDs, meter IDs, or any identifiers that could identify a person or account
- Internal URLs, hostnames, or IP addresses

Use environment variables or a `.env` file (git-ignored) for all runtime secrets and configuration. When adding new config, add the key with an empty/example value to `.env.example` instead.
