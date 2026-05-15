## 1. Dynamic Versioning

- [x] 1.1 In `pyproject.toml`: replace `version = "0.1.0"` with `dynamic = ["version"]`; replace `[build-system]` with `hatchling` backend and `hatch-vcs` in requires; add `[tool.hatch.version] source = "vcs"` section
- [x] 1.2 Add `src/oomi_influx/_version.py` to `.gitignore`
- [x] 1.3 Verify `uv build` succeeds and wheel metadata shows correct version when a `vX.Y.Z` tag is present (run locally against `v0.1.0` bootstrap tag)

## 2. Bootstrap Tag

- [x] 2.1 Create annotated tag `v0.1.0` on the current HEAD: `git tag -a v0.1.0 -m "v0.1.0"` and push it: `git push origin v0.1.0`

## 3. PyPI Trusted Publishing Setup (one-time manual)

- [x] 3.1 Create the PyPI project `oomi-influx` (or verify it exists) by doing a manual first publish OR via the PyPI "reserve name" flow
- [x] 3.2 In PyPI → Manage project → Publishing → Add a Trusted Publisher: Owner = `{gh-owner}`, Repo = `oomi-influx`, Workflow = `ci-publish.yml`, Environment = (leave blank)

## 4. Publish Workflow

- [x] 4.1 Create `.github/workflows/ci-publish.yml` with trigger `on: release: types: [published]`, runner `ubuntu-latest`, Python 3.13, `uv build`, and `pypa/gh-action-pypi-publish` with `id-token: write`

## 5. Release Skill

- [x] 5.1 Create `.claude/skills/release/skill.md` implementing the conventional-commit analysis, SemVer bump selection, release-notes grouping, confirmation via `AskUserQuestion`, and `gh release create` invocation
- [x] 5.2 Register the skill in `.claude/settings.json` (or verify it is auto-discovered from `.claude/skills/`)

## 6. Documentation

- [x] 6.1 Add a "Releasing" section to `CONTRIBUTING.md` covering: Trusted Publishing one-time setup, how to run `/release`, and how to verify the PyPI publish workflow ran
