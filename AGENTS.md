# AGENTS.md

A note about this file.
`AGENTS.md` is the single source of truth for repository-level agent guidance.
`CLAUDE.md` is just a symlink to `AGENTS.md` to ensure compatibility with Claude.
Do not treat `CLAUDE.md` as a separate file or try to edit it to keep it in sync with `AGENTS.md`

## Project Overview

This repository contains shareable agent skills — reusable, installable prompts that give agents specialized knowledge and workflows.
Skills live under `skills/`, each providing distributed agent-facing guidance and assets.
Development-only tests, generators, and other validation artifacts live under `dev/skills/`.

## Repository Structure

Important top-level paths:

- `skills/` - first-party skills authored in this repository.
    These are the skill files you may edit.
- `.agents/skills/` - installed dependency/support skills used while developing the first-party skills in this repository.
    Treat these as read-only inputs. Never edit files under this directory as part of work on this repo.
- `docs/` - Zensical-backed site content for human-facing documentation.
- `prompts/` - Saved prompts used in development and testing, not distributed with skills.
- `.github/` - CI and repository automation
- `pyproject.toml` - Pixi environment, tool dependencies, and `mdformat` config
- `.pre-commit-config.yaml` - canonical lint, format, and check definitions
- `.markdownlint.yaml` - Markdown lint rules tuned to the repo's formatting style
- `skills-lock.json` - pinned external skill dependencies and metadata
- `zensical.toml` - documentation site configuration

Current first-party skills live under `skills/`

- `datapackage/` - generic Frictionless Data Package exploration skill
- `pudl/` - PUDL data-user skill

Python utilities for use by agents in skills live under paths like `skills/<skill>/scripts/`.
These are small CLI tools not a large application framework.

## Distribution Boundary

Everything under `skills/<skill_name>/` is shipped with installed skills, including `SKILL.md`, `references/`, `assets/`, and (when present) `scripts/`.
Do not mention repository-internal dev paths, test suites, or example-generation scripts in distributed skill content (for example, anything under `dev/skills/`).
If guidance needs those artifacts at runtime, move the required artifacts into the distributed skill first.

Use `ALL_CAPS.md` only for repository standards or canonical interface files such as `AGENTS.md`, `README.md`, and `SKILL.md`.
Use kebab-case for other markdown documents.

The main goals when working here are:

- keep skill instructions and references accurate, concise, and easy for agents to consume
- preserve existing formatting, frontmatter, and repository conventions
- prefer updating source data or generator scripts over hand-editing generated outputs

```
agent-skills/
├── skills/
│   ├── datapackage/     # Generic Frictionless Data Package exploration skill
│   │   ├── SKILL.md           # Skill descriptor (YAML front matter) + usage guide
│   │   ├── assets/            # Distributed JSON schemas and skill assets
│   │   ├── references/        # frictionless-validate.md, metadata-querying.md, storage-backends.md
│   │   └── scripts/           # utility scripts (Python or shell) for use at runtime by agents
│   ├── pudl/            # PUDL data-user skill (read tables, explore metadata)
├── docs/                # Zensical documentation site source (markdown)
├── .github/workflows/   # CI: test-datapackage.yml, docs.yml
├── pyproject.toml       # Pixi workspace: dependencies, tasks, tool config
├── skills-lock.json     # Pinned external skill versions and hashes
└── .pre-commit-config.yaml
```

## Skill And Reference File Norms

Skill files and supporting references are the main product here; preserve their structure.

- keep YAML frontmatter valid and minimal
- maintain the established section layout in `SKILL.md` files unless there is a good reason to redesign it
- prefer references and cached artifacts for large factual lookups instead of bloating `SKILL.md`
- write instructions for agents, not marketing copy for humans
- keep examples realistic and copyable
- describe the skill as it works now, never relative to a prior version ("used to", "we removed", "no longer") — that history belongs in commit messages, not shipped content

Reference documents in `references/` are the authoritative source for reusable patterns.
Tests exist to validate those patterns and should stay in sync with them.

Each skill directory generally follows this layout:

```text
skills/<name>/
├── SKILL.md       # Required: YAML front matter descriptor + usage guide
├── assets/        # Schemas, cached data, and distributed skill assets
├── references/    # Long-form reference docs (markdown)
└── scripts/       # Utility scripts (Python or shell) for use at runtime by agents

dev/skills/<name>/
├── assets/examples/ # Generated example datasets and fixtures
├── scripts/         # Dev-only utility scripts (Python or shell)
├── tests/           # pytest suite verifying reference code examples
└── evals/           # Evaluation cases for measuring skill quality — dev-only, never shipped with the installed skill
```

- Reference documents in `references/` are the authoritative source for patterns.
    Test files exist solely to validate those patterns; keep them in sync.
- Files marked `linguist-generated=true` in `.gitattributes` are generated outputs — never hand-edit them.
    Regenerate them using the script that produced them.
- When adding a test suite to a skill, add a corresponding GitHub Actions workflow under `.github/workflows/` to run the tests in CI.
- External skills are managed through `skills-lock.json`, not added to the repo directly.
    They land in `.agents/skills/` (git-ignored) after `pixi run install-skills`.

### Layered Skills

Prefer linking layered skills to shared references instead of duplicating content.

That means:

- generic knowledge belongs in the lower-level skill that owns it
- higher-level skills should reference that shared guidance and add only domain-specific or workflow-specific context
- when a shared reference already exists, link to it instead of maintaining a second copy

In this repository:

- `datapackage` owns generic datapackage querying and loading patterns.
- `pudl` layers PUDL-specific data and metadata context on top of `datapackage`

If a skill depends on another skill conceptually, make that dependency explicit in the skill's frontmatter or instructions.
Never copy large blocks of text from one skill's references into another skill's references.

## Reference/Test Synchronization

Reference markdown examples are executable specifications for agent behavior.
When you update a documented workflow, keep its corresponding tests in sync so guidance remains reliable.

When editing a documented workflow snippet:

1. Update the snippet in `skills/<skill>/references/`.
1. Update the relevant tests in `dev/skills/<skill>/tests/`.
1. Run the relevant skill test suite.

Tests should validate the documented workflow pattern (API shape, operation, and result form), not incidental fixture details unless those details are explicitly part of the instructions.

## Markdown Conventions

- Treat `pyproject.toml` and `.markdownlint.yaml` as authoritative for Markdown formatting behavior.
- `mdformat` is configured with `wrap = "no"`; do not manually hard-wrap paragraphs.
- Use "semantic line breaks": one sentence per line, with blank lines between paragraphs.
    This makes diffs cleaner while preserving readability in raw form.
- `.markdownlint.yaml` disables or relaxes several rules to match the repo's authoring style.
    Do not "fix" those patterns unless the config changes.
- Four-space indentation for nested list content is the expected style.
- Raw HTML may be valid and intentional in Zensical content.
- Some files contain fenced code blocks, tabs, frontmatter, Mermaid blocks, or generated tables.
    Preserve those structures.

When editing Markdown:

- preserve existing frontmatter exactly unless the task requires changing it
- keep explanations concrete and directive rather than promotional
- prefer small edits over broad rewrites
- re-run `mdformat` and `markdownlint-cli2` on the changed files

## Docs And Site Content

The docs site is configured through `zensical.toml`.
When working on content under `docs/`, preserve Zensical-compatible Markdown features already in use.
This includes features such as admonitions, tabs, and other extended Markdown syntax.
If you need to run docs tooling, run Zensical through Pixi rather than assuming a global install.
Edit source files in `docs/`.
Never commit the built `site/` output.

## Python And Script Conventions

Python in this repository is mostly utility scripting. Follow the style already present in `skills/*/scripts/`.

- use `pathlib.Path` for filesystem work
- add explicit type hints where they improve readability
- prefer small helper functions over large inline script bodies
- keep top-of-file module docstrings accurate when behavior changes
- use UTF-8 when reading or writing text files
- prefer standard library solutions unless a repo dependency is already the right fit

When changing substantive script behavior, update docstrings and inline usage guidance to match.
Shell scripts should be POSIX-compatible. The repository validates them with `shellcheck`.
Every tool or runtime invoked directly should be listed as an explicit dependency in `pyproject.toml`.
Do not rely on transitive dependencies remaining available.

## Environment and Commands

This repository uses **pixi** for dependency and environment management.
All commands must be run through pixi.
Use `pixi` for all repository-local commands.
Do not use `uv`, `pip`, or ad hoc global tools when a repo-configured tool exists.
External skills (from `skills-lock.json`) are installed into `.agents/skills/`, which is git-ignored.
Install them with `pixi run install-skills`.

Useful repo tasks:

- `pixi run install-skills` - install the external skills pinned in `skills-lock.json`
- `pixi run test-datapackage` - run the datapackage reference-example test suite
- `pixi run test-pudl` - run the pudl reference-example test suite
- `pixi run test` - run every skill's test suite in one command

This repository targets modern Python only; do not add `from __future__ import annotations`.

## Linters, formatters, and validation workflow

This repository uses pre-commit hooks to enforce formatting and linting standards.
They are configured in `.pre-commit-config.yaml` and run by `prek`.
For broad validation, prefer the repo's pre-commit configuration instead of inventing one-off command combinations:

- `pixi run prek run --files ...`
- `pixi run prek run --all-files`

For iterative development call the underlying tools directly rather than routing everything through `prek`.
Direct invocation is faster, targets only the files you changed, and works on new files without staging them first.
**Determine which files to check from `git status`, not from memory.**
Determine which files to validate from `git status --short`, not from memory.
Any file may be modified by a formatter, a merge, or another tool after you last ran a check.

After editing, validate only the files you changed unless the task explicitly calls for a broader sweep.

Use `git status --short` to decide which files need checking.

- Python: `ruff check --fix`, `ruff format`, and `ty check` when Python changes are relevant
- Markdown: `mdformat` and `markdownlint-cli2`
- JSON: `pixi run prek run pretty-format-json --files ...`
- YAML: `prettier --write`
- GitHub Actions workflows: `actionlint`
- TOML: `taplo format`
- spelling-sensitive docs: `typos` when appropriate

Prefer these patterns:

- `pixi run ruff check --fix path/to/file.py`
- `pixi run ruff format path/to/file.py`
- `pixi run ty check`
- `pixi run markdownlint-cli2 path/to/file.md`
- `pixi run mdformat path/to/file.md`
- `pixi run prettier --write path/to/file.yaml`
- `pixi run taplo format path/to/file.toml`
- `pixi run typos path/to/file.md`
- `pixi run actionlint path/to/workflow.yml`

If a task touches multiple file types, prefer `pixi run prek run --files ...` once the individual file-level checks have been run.

- **Explicit dependencies**: Every tool or runtime invoked directly must be listed as an explicit dependency in `pyproject.toml`.
    Do not rely on transitive dependencies — they are an implementation detail of another package and can disappear without warning if that package changes.
    Add missing dependencies with `pixi add <package>`.
- **Typos**: The `typos` checker excludes `skills/*/assets/` and certain generated reference tables because upstream data may contain canonical misspellings.
    Do not add spurious typo suppressions elsewhere.
- **Line endings**: LF only. The `mixed-line-ending` hook enforces this; do not commit CRLF line endings.
- **Shell scripts**: Write POSIX-compatible shell.
    The `shellcheck` hook validates all shell scripts.
- **Python type checking**: `ty` runs as a pre-commit hook locally but is skipped in CI (`ci: skip: [ty-check]` in `.pre-commit-config.yaml`).
    Always run it locally before committing Python changes.
- **Documentation**: The `docs/` site is built with Zensical and deployed by CI on push to `main`.
    Edit source files in `docs/` (markdown); never commit the `site/` build output.
- **Large files**: The `check-added-large-files` hook is configured at 800 KB to catch accidental large-file additions.
    Treat that threshold as a prompt to confirm intent, not as a blanket prohibition on larger generated artifacts.
- **Type checking**: `ty` is intentionally run over the whole repository.
    It is fast enough not to be burdensome here, and project-wide checking catches cross-file import, symbol redefinition, and interface drift issues that file-scoped checks can miss.
    The `ty` hook is skipped in CI, so run it locally after making Python changes.
- **JSON formatting**: The `pretty-format-json` hook uses specific arguments (`--autofix --indent=2 --no-sort-keys`).
    Calling it through `prek` is simpler than replicating them.
    Python code that writes JSON must use `indent=2` and the default `ensure_ascii=True` — do **not** pass `ensure_ascii=False`.

## Change Scope

Keep changes focused.

- do not reformat unrelated files
- do not rewrite large reference documents unless the task requires it
- do not replace repo-specific commands with generic alternatives
- do not remove generated-content markers or explanatory comments that other scripts rely on

When you are unsure whether a section is generated or hand-maintained, inspect nearby
comments and the corresponding `skills/*/scripts/` directory before editing.

## Generated Content

Several files in this repository are wholly or partly generated.
Do not hand-edit generated table bodies or generated data files if a generator owns them.
This includes all the files under `dev/skills/datapackage/assets/examples/`

Common patterns in this repo:

When you add a new code example to any reference file, add a corresponding test to the appropriate test file that runs the pattern against the example data.
Check `dev/skills/<skill>/tests/conftest.py` for shared constants (row counts, column names, path roots) before adding new helpers.

- sentinel comments that mark generated regions
- JSON sidecars or cached metadata used to render tables
- files marked `linguist-generated=true` in `.gitattributes`
- utility scripts under `skills/*/scripts/` that regenerate sections or datasets

After modifying `dev/skills/datapackage/scripts/generate_examples.py`, regenerate all example datasets and verify nothing regressed:

- edit the source data, cached metadata, or generator script
- regenerate the output
- avoid manual cleanup edits inside the generated region

```bash
python dev/skills/datapackage/scripts/generate_examples.py
pixi run test-datapackage
pixi run prek run pretty-format-json --all-files  # reformat generated descriptors
```

## Datapackage Skill Rules

Datapackage repository-maintainer notes (example corpus layout, regeneration workflow, and other dev-only context) are documented in `dev/skills/datapackage/datapackage-dev-guide.md`.
See [Generated Content](#generated-content) above for the test/regeneration workflow.

## PUDL Skill Rules

PUDL repository-maintainer notes (test fixture layout and the offline descriptor sample's regeneration workflow) are documented in `dev/skills/pudl/pudl-dev-guide.md`.
