## Why

There is no automated release pipeline: publishing to PyPI, version management, and changelog generation all require manual work. Establishing a standard, tag-driven release flow eliminates manual busywork and ensures every release is reproducible and traceable.

## What Changes

- Switch `pyproject.toml` from a static version string to `hatch-vcs` dynamic versioning so the version is always derived from the current git tag at build time — no version ever lives in source.
- Add a GitHub Actions **publish** workflow (`ci-publish.yml`) triggered by GitHub Release publication; it builds a wheel + sdist with `uv build` and pushes to PyPI via OIDC Trusted Publishing (no stored secrets).
- Add a Claude Code **`/release` skill** that analyses conventional commits since the last tag, determines the correct SemVer bump, drafts release notes, and creates the GitHub Release (and therefore the git tag) with a single confirmation.

## Capabilities

### New Capabilities

- `dynamic-versioning`: Replace `version = "0.1.0"` in `pyproject.toml` with `hatch-vcs`; version is read from the nearest git tag at build/install time.
- `pypi-publish`: GitHub Actions workflow that triggers on every published GitHub Release, builds the package, and uploads to PyPI using Trusted Publishing (OIDC).
- `release-skill`: A `.claude/skills/release/` Claude Code skill (`/release`) that computes the SemVer bump from conventional commits, shows a release-notes preview, and on confirmation calls `gh release create` to publish the GitHub Release.

### Modified Capabilities

_(none)_

## Impact

- `pyproject.toml`: `version` field replaced with `dynamic`; `hatch-vcs` added to `[build-system]`.
- `.github/workflows/ci-publish.yml`: new file.
- `.claude/skills/release/`: new skill directory with `skill.md`.
- PyPI project must be pre-created and Trusted Publishing configured (one-time manual step, documented in CONTRIBUTING.md).
- No Python source files change; `__version__` remains absent.

## Non-goals

- Automated merging or branch protection rule changes.
- Changelog file (`CHANGELOG.md`) generation — GitHub Release notes serve this purpose.
- Multi-environment (staging/production) deployment beyond PyPI.
- PR-level preview builds or test PyPI publishing.
