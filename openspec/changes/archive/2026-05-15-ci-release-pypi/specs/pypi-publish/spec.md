## ADDED Requirements

### Requirement: Publish workflow triggered by GitHub Release publication
A GitHub Actions workflow file `.github/workflows/ci-publish.yml` SHALL trigger on `release: types: [published]` and upload the built package to PyPI.

#### Scenario: Workflow fires on release published
- **WHEN** a GitHub Release is set to Published (not Draft)
- **THEN** the `ci-publish` workflow starts within GitHub Actions

#### Scenario: Workflow does not fire on draft releases
- **WHEN** a GitHub Release is saved as Draft
- **THEN** no publish workflow run is triggered

### Requirement: Build produces wheel and sdist
The publish workflow SHALL run `uv build` to produce both a wheel (`.whl`) and a source distribution (`.tar.gz`) before uploading.

#### Scenario: Build artifacts present before upload
- **WHEN** the build step completes
- **THEN** the `dist/` directory contains exactly one `.whl` and one `.tar.gz`

### Requirement: Upload to PyPI via OIDC Trusted Publishing
The workflow SHALL use `pypa/gh-action-pypi-publish` with `id-token: write` permission. No API token or password SHALL be stored as a GitHub secret.

#### Scenario: Publish succeeds without any stored credentials
- **WHEN** the publish step runs with `id-token: write` granted
- **THEN** the OIDC exchange succeeds and the package appears on PyPI under the release version

### Requirement: Workflow runs on ubuntu-latest with Python 3.13
The publish workflow's runner SHALL be `ubuntu-latest` and use Python 3.13 to match the project's minimum Python version.

#### Scenario: Python version matches project minimum
- **WHEN** the workflow installs Python
- **THEN** `python --version` outputs `Python 3.13.x`
