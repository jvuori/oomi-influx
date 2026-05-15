# Spec: dynamic-versioning

## Purpose

Derive the package version exclusively from annotated git tags at build time using hatchling and hatch-vcs, eliminating any static version string from source files.

## Requirements

### Requirement: Version derived from git tag at build time
The package version SHALL be determined exclusively from annotated git tags matching `vX.Y.Z`. No version string SHALL appear in `pyproject.toml` or any Python source file tracked by git.

#### Scenario: Clean tag checkout produces exact version
- **WHEN** the working tree is checked out exactly at an annotated tag `v1.2.3`
- **THEN** `python -c "import oomi_influx; print(oomi_influx.__version__)"` outputs `1.2.3`

#### Scenario: Untagged commit produces dev version
- **WHEN** the working tree has commits after the last tag
- **THEN** the version string includes a `.devN+gSHA` suffix, indicating an unreleased build

#### Scenario: pyproject.toml contains no static version
- **WHEN** a developer reads `pyproject.toml`
- **THEN** the `version` key is absent and `dynamic = ["version"]` is present under `[project]`

### Requirement: Build backend switched to hatchling with hatch-vcs
The `[build-system]` in `pyproject.toml` SHALL use `hatchling` as the backend and `hatch-vcs` as the version source. `uv build` SHALL produce a wheel and sdist with correct metadata.

#### Scenario: uv build succeeds with version from tag
- **WHEN** `uv build` is run on a commit tagged `v0.2.0`
- **THEN** the resulting wheel filename contains `oomi_influx-0.2.0` and `PKG-INFO` shows `Version: 0.2.0`

### Requirement: Generated version file is excluded from git
The file `src/oomi_influx/_version.py` written by `hatch-vcs` at build time SHALL be listed in `.gitignore` and SHALL NOT be committed.

#### Scenario: _version.py absent from tracked files
- **WHEN** `git ls-files src/oomi_influx/_version.py` is run
- **THEN** the command returns no output (file is untracked)
