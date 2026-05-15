## Context

`oomi-influx` is a small CLI + library package built with `uv` / `uv_build`. Currently `version = "0.1.0"` is a static string in `pyproject.toml`. There is no CI/CD, no PyPI presence, and releases are entirely manual. The build backend is `uv_build` (the uv native backend).

## Goals / Non-Goals

**Goals:**
- Version derived solely from git tags; `pyproject.toml` never needs touching for a release.
- One GitHub Release creation triggers the full publish pipeline automatically.
- A Claude Code skill makes the decision-making part of releasing (semver bump + notes) fast and interactive.

**Non-Goals:**
- Automated release on every merge to main — the engineer decides when to release.
- Changelog file in repo (GitHub Releases ARE the changelog).
- TestPyPI staging or pre-release publishing.

## Decisions

### 1. Dynamic versioning: `hatch-vcs` (not `setuptools-scm` directly)

`uv_build` does not natively support VCS versioning. We switch the build backend to `hatchling` + `hatch-vcs`. `hatch-vcs` calls `setuptools-scm` internally, reads the nearest annotated git tag (`vX.Y.Z`), and writes `src/oomi_influx/_version.py` at build time. The generated file is `.gitignore`d.

**Why hatchling over setuptools?** `uv` supports `hatchling` natively in its build pipeline; the lock file and workspace features continue to work without changes. `uv_build` → `hatchling` is a one-line swap.

**Why not `uv_build` with an `--override-version` flag at publish time?** That still requires the GitHub Action to edit `pyproject.toml` or pass an env var — not cleaner than a proper VCS backend, and it diverges from what `pip install git+...` or `uv add git+...` users would get.

### 2. PyPI publishing: OIDC Trusted Publishing (no API tokens)

GitHub Actions natively supports PyPI Trusted Publishing via the `id-token: write` permission. The `pypa/gh-action-pypi-publish` action exchanges the job's OIDC token for a short-lived PyPI upload credential. No secrets are stored in GitHub or PyPI.

Trigger: `on: release: types: [published]` — meaning the workflow fires exactly when a GitHub Release is marked Published (not just drafted).

**Why not `uv publish`?** `uv publish` does not yet support OIDC Trusted Publishing as of mid-2025; it requires an API token. `twine` via `pypa/gh-action-pypi-publish` is the canonical OIDC path.

### 3. Release skill: `gh release create` is the primitive

The `/release` skill's job is cognitive, not mechanical:
1. `git log v{last}..HEAD --pretty=format:"%s"` → parse conventional commit subjects.
2. Map types: `feat` → minor, `fix|perf|refactor` → patch, `BREAKING CHANGE` in footer → major.
3. Group commits into a markdown release-notes body.
4. `AskUserQuestion` for confirmation / override of the bump.
5. `gh release create v{new} --title "v{new}" --notes "{body}" --target HEAD` — this creates the annotated tag AND the GitHub Release in one call.

The GitHub Actions publish workflow then fires automatically from the release event.

### 4. Annotated tags vs lightweight tags

`hatch-vcs` / `setuptools-scm` requires **annotated** tags (`git tag -a`) to produce clean version strings without `.devN` suffixes. `gh release create` creates annotated tags by default — this is correct behaviour with no extra steps.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `hatchling` adds a build-time dep not in `uv.lock` | Add `hatchling` and `hatch-vcs` to `[build-system].requires` — `uv` picks them up automatically. |
| Skill misclassifies a commit type | Confirmation step; engineer can override the bump before the release is created. |
| PyPI Trusted Publishing must be configured once manually | Document the one-time setup clearly in `CONTRIBUTING.md`. |
| `gh release create` requires `gh` CLI authenticated in local env | Skill documents this pre-condition; common for developers who already use `gh`. |
| First release has no prior tag | Skill falls back to the repo's initial commit when no tag exists; documents this edge case. |

## Migration Plan

1. Update `pyproject.toml`: swap build backend, add `hatch-vcs`, remove static version.
2. Create `src/oomi_influx/_version.py` stub (import guard) and add to `.gitignore`.
3. Add `.github/workflows/ci-publish.yml`.
4. Add `.claude/skills/release/skill.md`.
5. Create PyPI project manually and configure Trusted Publishing (one-time, documented).
6. Tag `v0.1.0` to bootstrap the version history.
