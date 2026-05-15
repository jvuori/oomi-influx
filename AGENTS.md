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
- Keep the dependency surface **as small as possible** — every dependency is an attack surface and an upgrade burden.
- Prefer packages from the Python scientific / data ecosystem (e.g. `httpx`, `influxdb-client`, `pydantic`) over obscure alternatives.

## Test-driven development

When fixing a bug:

1. Write a **failing test** that reproduces the bug first.
2. Verify the test fails for the right reason.
3. Apply the fix.
4. Verify the test now passes.

A fix without a preceding failing test is not acceptable.

## Linting and quality

Before every commit:

1. `uv run ruff check --fix .`
2. `uv run ruff format .`
3. `uv run ty check .`
4. `uv run pytest`

All four must pass with no errors before changes are committed.

## Error handling and defensive programming

- **Prefer raising exceptions over silently coping.** If something is wrong, throw an exception and let it surface as a traceback. Do not write code that tries to paper over incorrect behaviour.
- Never swallow exceptions with bare `except: pass` or catch-all handlers that hide the root cause.
- Avoid silent fallbacks (e.g. returning `None`, `""`, or `0`) when the absence of a value indicates a real error condition.
- Validate assumptions with `assert` or explicit `raise` statements rather than hoping downstream code will detect the problem.

## Git commit messages

- Never include `Co-Authored-By` lines in commit messages.

## Security — never commit personal or sensitive data

The following must **never** be stored in Git (this will be a public repository):

- Credentials, passwords, tokens, API keys, or secrets of any kind
- Personal data: names, email addresses, phone numbers
- Subscription IDs, account IDs, meter IDs, or any identifiers that could identify a person or account
- Internal URLs, hostnames, or IP addresses

Use environment variables or a `.env` file (git-ignored) for all runtime secrets and configuration. When adding new config, add the key with an empty/example value to `.env.example` instead.
