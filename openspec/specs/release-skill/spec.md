# Spec: release-skill

## Purpose

Provide a `/release` Claude Code skill that automates SemVer releases by analysing conventional commits, drafting release notes, confirming with the engineer, and creating the GitHub Release (which in turn triggers PyPI publish).

## Requirements

### Requirement: Skill analyses conventional commits since last tag
The `/release` skill SHALL inspect `git log` from the most recent annotated tag to `HEAD` and parse conventional commit subjects to determine the appropriate SemVer bump.

#### Scenario: feat commit bumps minor version
- **WHEN** commits since the last tag include at least one `feat:` subject
- **THEN** the skill proposes a minor version bump (e.g. `1.0.0` → `1.1.0`)

#### Scenario: breaking change bumps major version
- **WHEN** any commit subject contains `!:` or the commit body contains `BREAKING CHANGE:`
- **THEN** the skill proposes a major version bump (e.g. `1.2.3` → `2.0.0`)

#### Scenario: only fix/chore/refactor/perf commits bump patch
- **WHEN** all commits since the last tag are of type `fix`, `chore`, `refactor`, `perf`, `docs`, `test`, or `ci`
- **THEN** the skill proposes a patch version bump (e.g. `1.2.3` → `1.2.4`)

#### Scenario: no tag exists yet
- **WHEN** there are no annotated tags in the repository
- **THEN** the skill assumes the last release was `v0.0.0` and proposes `v0.1.0` as the first release

### Requirement: Skill presents draft release notes grouped by commit type
Before creating the release, the skill SHALL display the proposed version, the computed SemVer bump rationale, and release-notes markdown grouped under headings (e.g. `### Features`, `### Bug Fixes`, `### Other Changes`).

#### Scenario: Release notes shown before confirmation
- **WHEN** the skill has analysed the commits
- **THEN** it displays the draft notes and asks the engineer to confirm or change the version bump before proceeding

#### Scenario: Engineer overrides the proposed bump
- **WHEN** the engineer selects a different bump level (major/minor/patch) than proposed
- **THEN** the skill recalculates the target version accordingly

### Requirement: Skill creates GitHub Release with a single confirmation
After confirmation, the skill SHALL execute `gh release create v{version} --title "v{version}" --notes "{body}"` targeting `HEAD`. It SHALL NOT create the tag separately — `gh release create` creates the annotated tag implicitly.

#### Scenario: Release and tag created together
- **WHEN** the engineer confirms the release
- **THEN** `gh release create` is called once, both the annotated tag and the GitHub Release appear, and the CI publish workflow is triggered automatically

#### Scenario: Skill aborts cleanly on denial
- **WHEN** the engineer cancels at the confirmation step
- **THEN** no tag is created, no release is published, and no gh commands are run

### Requirement: Skill is located at `.claude/skills/release/skill.md`
The skill file SHALL be placed at `.claude/skills/release/skill.md` and invocable as `/release` inside Claude Code sessions.

#### Scenario: Skill discoverable by Claude Code
- **WHEN** a developer types `/release` in a Claude Code session within this repository
- **THEN** the skill is loaded and executed
